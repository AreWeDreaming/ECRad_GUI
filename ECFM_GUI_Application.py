# -*- coding: utf-8 -*-
import re
import os
import wx
import sys
sys.path.append("../ECFM_Pylib")
from GlobalSettings import AUG, TCV, Phoenix
from plotting_configuration import *
import wx.lib.agw.toasterbox as TB
from ECRad_GUI_LaunchPanel import Launch_Panel
from ECRad_GUI_ScenarioPanel import ScenarioSelectPanel
from ECRad_GUI_Widgets import simple_label_tc, simple_label_cb, max_var_in_row
# import  wx.lib.scrolledpanel as ScrolledPanel
import numpy as np
from signal import signal, SIGTERM
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
if(Phoenix):
    from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar2Wx
else:
    from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx
from Diags import Diag, ECRH_diag, ECI_diag, EXT_diag, TCV_diag
from wxEvents import *
from ECFM_GUI_Thread import WorkerThread
from plotting_core import plotting_core
import glob
# from ECFM_GUI_IO import test_func
from ECFM_GUI_Exceptions import ConfigInputException
from ECFM_GUI_Exceptions import ConfigOutputException
from ECFM_GUI_Shell import Redirect_Text
from collections import OrderedDict as od
from ECFM_Interface import prepare_input_files, GetECFMExec
from TB_communication import make_all_TORBEAM_rays_thread, make_LUKE_data, make_LUKE_input_mat
from electron_distribution_utils import Gene, Gene_BiMax
from ECFM_Results import ECFMResults
import getpass
from ECFM_GUI_Calibration import calibrate
from Fitting import make_fit
ECFM_Model = False
import shutil
from time import sleep

# Events


def kill_handler(signum, frame):
    print 'Successfully terminated ECFM with Signal ', signum



class ECFM_GUI_App(wx.App):
    def OnInit(self):
        self.SetAppName("ECRad GUI")
        if(Phoenix):
            frame = ECFM_GUI_MainFrame(self, 'ECRad GUI')
            self.SetTopWindow(frame)
            frame.Show(True)
        return True

class ECFM_GUI_MainFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, None, wx.ID_ANY, title, \
                          style=wx.DEFAULT_FRAME_STYLE | \
                          wx.FULL_REPAINT_ON_RESIZE)
        self.FrameParent = parent
        self.statusbar = self.CreateStatusBar(2)  # , wx.ST_SIZEGRIP
        self.statusbar.SetStatusWidths([-2, -1])
        self.Bind(EVT_NEW_STATUS, self.SetNewStatus)
        self.Bind(EVT_RESIZE, self.OnResizeAll)
        self.CreateMenuBar()
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Panel = Main_Panel(self)
        self.sizer.Add(self.Panel, 1, wx.EXPAND)
        self.OldSize = self.GetSize()
        self.ConfigLoaded = False

        # if(ECFM_Model):
        #    self.ECFM_Ext_window = ECFM_Ext.ECFM_GUI_ECFM_Ext_Frame(self)
        #    self.ECFM_Ext_window.Show()
        #    self.ECFM_Ext_window.Raise()
        #    self.ECFM_Ext_window.Center()
        self.SetSizer(self.sizer)
#        self.SetClientSize(self.Panel.sizer.GetMinSize())
#        self.PlotWindow = PlotFrame(self)
        self.SetClientSize((wx.GetDisplaySize()[0] * 0.8, \
                            wx.GetDisplaySize()[1] * 0.8))
        self.Center()


    def SetNewStatus(self, evt):
        self.statusbar.SetStatusText(evt.Status)

    def CreateMenuBar(self):
        self._menuBar = wx.MenuBar(wx.MB_DOCKABLE)
        self._fileMenu = wx.Menu()
        self._editMenu = wx.Menu()
        self.ECFM_config_load = wx.MenuItem(self._fileMenu, wx.ID_ANY, text=\
            "Load preexisting calculation")
        self.Hide_Config = wx.MenuItem(self._fileMenu, wx.ID_ANY, text=\
            'Hide the Input Mask')
        self.Show_Config = wx.MenuItem(self._fileMenu, wx.ID_ANY, text=\
            'Show the Input Mask')
        self.ECFM_quit = wx.MenuItem(self._fileMenu, wx.ID_ANY, \
                                "&Close\tCtrl-Q", "Close ECFM_GUI")
        if(Phoenix):
            self._fileMenu.Append(self.ECFM_config_load)
            self._fileMenu.Append(self.ECFM_quit)
        else:
            self._fileMenu.AppendItem(self.ECFM_config_load)
            self._fileMenu.AppendItem(self.ECFM_quit)
        self._menuBar.Append(self._fileMenu, "&File")
        # self._fileMenu.AppendItem(self.Hide_Config)
        # self._fileMenu.AppendItem(self.Show_Config)
        self.SetMenuBar(self._menuBar)
        self.Bind(wx.EVT_MENU, self.OnOpenOldFile, self.ECFM_config_load)
        self.Bind(wx.EVT_MENU, self.OnHideConfig, self.Hide_Config)
        self.Bind(wx.EVT_MENU, self.OnShowConfig, self.Show_Config)
        self.Bind(wx.EVT_MENU, self.OnQuit, self.ECFM_quit)
        self.Bind(wx.EVT_CLOSE, self.OnQuit, self)


    def OnHideConfig(self, evt):
        if(self.ConfigLoaded and self.Panel.NotebookPanel.IsShown()):
            self.Panel.NotebookPanel.Show(False)

    def OnShowConfig(self, evt):
        if(self.ConfigLoaded and not self.Panel.NotebookPanel.IsShown()):
            self.Panel.NotebookPanel.Show(True)

    def OnOpenOldFile(self, evt):
        dlg = wx.FileDialog(\
            self, message="Choose a preexisting calculation", \
            defaultDir=self.Panel.Config.working_dir, \
            wildcard=('Matlab files (*.mat)|*.mat|All fiels (*.*)|*.*'),
            style=wx.FD_OPEN)
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            dlg.Destroy()
            evt = LoadMatEvt(Unbound_EVT_LOAD_MAT, self.Panel.GetId())
            evt.SetFilename(path)
            self.Panel.GetEventHandler().ProcessEvent(evt)

    def OnQuit(self, event):
        self.FrameParent.ExitMainLoop()
        self.Destroy()

    def OnResizeAll(self, evt):
        self.Layout()
        self.Refresh()

class Main_Panel(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, wx.ID_ANY)
        self.parent = parent
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.ECFM_running = False
        self.ECFM_process = None
        self.ECFM_pid = None
        self.stop_current_evaluation = False
        self.Results = ECFMResults()
        self.Bind(wx.EVT_END_PROCESS, self.OnProcessEnded)
        self.Bind(EVT_NEXT_TIME_STEP, self.OnNextTimeStep)
        self.Bind(EVT_UPDATE_CONFIG, self.OnConfigLoaded)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.Bind(EVT_LOCK_EXPORT, self.OnLockExport)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.SetSizer(self.sizer)
        self.SetSize((400, 400))
        self.SetMinSize((400, 400))
        self.data = None
        self.ControlSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ButtonSizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.ControlSizer, 0, wx.EXPAND | wx.ALL , 5)
        self.StartECFMButton = wx.Button(self, wx.ID_ANY, \
            'Start ECFM')
        self.KillECFMButton = wx.Button(self, wx.ID_ANY, 'Terminate ECFM')
        self.StartECFMButton.Bind(wx.EVT_BUTTON, self.OnStartECFM)
        self.KillECFMButton.Bind(wx.EVT_BUTTON, self.OnKillECFM)
        self.KillECFMButton.Disable()
        self.ExporttoMatButton = wx.Button(self, wx.ID_ANY, 'Export to .mat')
        if(Phoenix):
            self.ExporttoMatButton.SetToolTipString("If this is grayed out there is no (new) data to save!")
        else:
            self.ExporttoMatButton.SetToolTipString("If this is grayed out there is no (new) data to save!")
        self.ExporttoMatButton.Bind(wx.EVT_BUTTON, self.OnExporttoMat)
        self.ExporttoMatButton.Disable()
        self.Bind(EVT_LOAD_MAT, self.OnImportMat)
        username = "."
        if(getpass.getuser() == "sdenk"):
#            self.ExporttoNssfButton = wx.Button(self, wx.ID_ANY, 'Export to nssf')
#            self.ExporttoNssfButton.Bind(wx.EVT_BUTTON, self.OnExporttoNssf)
#            self.ExporttotokpNssfButton = wx.Button(self, wx.ID_ANY, 'Export to tokp nssf')
#            self.ExporttotokpNssfButton.Bind(wx.EVT_BUTTON, self.OnExporttotokpNssf)
            username = ", Severin."
        elif(getpass.getuser() == "bva"):
            username = ", Branka."
        elif(getpass.getuser() == "mwillens"):
            username = ", Matthias."
        elif(getpass.getuser() == "sfreethy"):
            username = ", Simon."
        self.ButtonSizer.Add(self.StartECFMButton, 0, wx.ALL | \
                        wx.LEFT, 5)
        self.ButtonSizer.Add(self.KillECFMButton, 0, wx.ALL | \
                        wx.LEFT, 5)
        self.ButtonSizer.Add(self.ExporttoMatButton, 0, wx.ALL | \
                        wx.LEFT, 5)
#        if(getpass.getuser() == "sdenk"):
#            self.ButtonSizer.Add(self.ExporttoNssfButton, 0, wx.ALL | \
#                        wx.LEFT, 5)
#            self.ButtonSizer.Add(self.ExporttotokpNssfButton, 0, wx.ALL | \
#                        wx.LEFT, 5)
        self.ControlSizer.Add(self.ButtonSizer, 0, wx.ALIGN_TOP)
        self.Log_Box = wx.TextCtrl(self, wx.ID_ANY, size=(500, 100), \
                style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.Log_Box.AppendText('Welcome to the ECRad GUI' + username + os.linesep)
        self.ControlSizer.Add(self.Log_Box, 1, wx.ALL | wx.EXPAND | \
                    wx.ALIGN_LEFT, 5)
        self.ProgressBar = wx.Gauge(self, wx.ID_ANY, style=wx.GA_HORIZONTAL)
        self.Progress_label = wx.StaticText(self, wx.ID_ANY, "No ECRad run in progress")
        self.Progress_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Progress_sizer.Add(self.ProgressBar, 1, wx.ALL | wx.EXPAND, 5)
        self.Progress_sizer.Add(self.Progress_label, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        self.Redirector = Redirect_Text(self.Log_Box)
        sys.stdout = self.Redirector
        self.InvokeECFM = None
        self.index = 0  # Index for the iteration over timepoints
        self.DoReflecOnly = False  # Only evaluate the reflection model in the next time step
        self.UpperBook = wx.Notebook(self)
        self.ConfigPage = Config_Page(self.UpperBook, self.Results.Config)
        self.UpperBook.AddPage(self.ConfigPage, "ECRad configuration")
        self.LaunchPanel = Launch_Panel(self.UpperBook, self.Results.Scenario)
        self.UpperBook.AddPage(self.LaunchPanel, "Diagnostic configuration")
        self.Scenario_Select_Panel = ScenarioSelectPanel(self.UpperBook, self.Results.Scenario, self.Results.Config)
        self.UpperBook.AddPage(self.Scenario_Select_Panel, "Select IDA time points")
        self.sizer.Add(self.Progress_sizer, 0, wx.ALL | wx.EXPAND, 5)
        self.SetScrollRate(20, 20)
        self.Calib_Panel = CalibPanel(self.UpperBook, self.Results.Scenario)
        self.UpperBook.AddPage(self.Calib_Panel, "ECFM Calibration")
        self.Calib_Evolution_Panel = CalibEvolutionPanel(self.UpperBook, self.Results.Config.working_dir)
        self.UpperBook.AddPage(self.Calib_Evolution_Panel, "Plotting for calibration")
        self.Plot_Panel = ECFM_GUI_LOS_PlotPanel(self.UpperBook)
        self.UpperBook.AddPage(self.Plot_Panel, "Misc. Plots")
        self.f_reflec = None
        self.Trad_X_reflec = None  # TRad for reflec_model = 1 -> X-mode
        self.tau_X_reflec = None  # TRad for reflec_model = 1 -> X-mode
        self.Trad_O_reflec = None  # TRad for reflec_model = 1 -> O-mode
        self.tau_O_reflec = None  # TRad for reflec_model = 1 -> X-mode
        self.sizer.Add(self.UpperBook, 1, wx.ALL | \
            wx.LEFT, 5)

    def __del__(self):
        if self.ECFM_process is not None:
            self.ECFM_process.Detach()
            self.ECFM_process.CloseOutput()
            self.ECFM_process = None



    def OnStartECFM(self, evt):
        if(self.ECFM_running):
            print('ECFM is still running - please wait!')
            return
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Preparing run - GUI might be unresponsive for minutes - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        try:
            self.Results.Config = self.ConfigPage.UpdateConfig(self.Results.Config)
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
        # Sets time points and stores plasma data in Scenario
        if(not self.Results.Scenario.plasma_set):
            try:
                self.Results.Scenario = self.Scenario_Select_Panel.LoadScenario(self.Results.Scenario, self.Results.Config, None)
                if(not self.Results.Scenario.plasma_set):
                    return
            except ValueError as e:
                print("Failed to load Scenario")
                print("Reason: " + e)
                return
        # Stores launch data in Scenario
        if(not self.Results.Scenario.diags_set):
            try:
                self.Results.Scenario = self.LaunchPanel.UpdateScenario(self.Results.Scenario)
                if(not self.Results.Scenario.diags_set):
                    return
            except ValueError as e:
                print("Failed to parse diagnostic info")
                print("Reason: " + e)
                return
        self.stop_current_evaluation = False
        if(len(self.Results.Scenario.used_diags_dict.keys()) == 0):
            print("No diagnostics selected")
            print("Run aborted")
            return
        if(len(self.Results.Scenario.plasma_dict["time"]) == 0):
            print("No time points selected")
            print("Run aborted")
            return
        if(self.Results.Config.dstf == "Re"):
            dlg = wx.DirDialog(self, \
                       message="Choose folder with distribution data", \
                       style=wx.DD_DIR_MUST_EXIST)
            if(dlg.ShowModal() == wx.ID_OK):
                self.Config.Relax_dir = dlg.GetPath()
                dlg.Destroy()
            else:
                print("Aborted Launch")
                return
        elif(self.Results.Config.dstf == "Ge" or self.Results.Config.dstf == "GB"):
            if(self.Config.dstf == "Ge"):
                self.Config.gene_obj = []
                self.Config.gene_obj.append(Gene(self.Config.working_dir, self.Config.shot, EQSlice=EQSlice, it=it))
                self.unused.append("{0:d}".format(0))
                if(self.Config.gene_obj[-1].total_time_cnt > 0):
                    for it in range(1, self.Config.gene_obj[-1].total_time_cnt):
                        self.Config.gene_obj.append(Gene(self.Config.working_dir, self.Config.shot, EQSlice=EQSlice, it=it))
                        self.unused.append("{0:d}".format(it))
            elif(self.Config.dstf == "GB"):
                self.Config.gene_obj = []
                self.Config.gene_obj.append(Gene_BiMax(self.Config.working_dir, self.Config.shot, EQSlice=EQSlice, it=it))
    #            self.unused.append("{0:d}".format(0))
                if(self.Config.gene_obj[-1].total_time_cnt > 0):
                    for it in range(1, self.Config.gene_obj[-1].total_time_cnt):
                        self.Config.gene_obj.append(Gene_BiMax(self.Config.working_dir, self.Config.shot, EQSlice=EQSlice, it=it))
                        self.unused.append("{0:d}".format(it))
        self.Results.Config.autosave()
        self.Results.Scenario.autosave()
        self.ProcessTimeStep()

    def ProcessTimeStep(self):
        if(os.path.isdir(os.path.join(self.Results.Config.working_dir, "ecfm_data"))):
            shutil.rmtree(os.path.join(self.Results.Config.working_dir, "ecfm_data"), ignore_errors=True)
        if(os.path.isfile(os.path.join(self.Results.Config.working_dir, "ECRad.o"))):
            os.remove(os.path.join(self.Results.Config.working_dir, "ECRad.o"))
        if(os.path.isfile(os.path.join(self.Results.Config.working_dir, "ECRad.e"))):
            os.remove(os.path.join(self.Results.Config.working_dir, "ECRad.e"))
        if(not prepare_input_files(self.Results.Config, self.Results.Scenario, self.index)):
            print("Error!! Launch aborted")
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('Error while preparing launch!')
            self.GetEventHandler().ProcessEvent(evt)
            return
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Successfully saved new values')
        self.GetEventHandler().ProcessEvent(evt)
        print('Successfully saved new values')
        self.ExporttoMatButton.Disable()
        self.InvokeECFM = GetECFMExec(self.Results.Config, self.Results.Scenario, self.Results.Scenario.plasma_dict["time"][self.index])
        os.environ['ECFM_WORKING_DIR'] = self.Results.Config.working_dir
        self.ECFM_running = True
        self.Progress_label.SetLabel("ECFM running - (1/{0:d})".format(len(self.Results.Scenario.plasma_dict["time"])))
        self.ProgressBar.SetValue(0)
        self.ECFM_process = wx.Process(self)
        self.ECFM_process.Redirect()
        print("-------- Launching ECFM -----------\n")
        print("-------- INVOKE COMMAND------------\n")
        print(self.InvokeECFM)
        print("-------- Current working directory ------------\n")
        print(os.getcwd())
        print("-----------------------------------\n")
        self.StartECFMButton.Disable()
#            ticket_manager = wx.Process(self)
#            ticket_manager_pid = wx.Execute("echo $KRB5CCNAME", \
#                                       wx.EXEC_SYNC, ticket_manager)
        self.ECFM_pid = wx.Execute(self.InvokeECFM, \
                                   wx.EXEC_ASYNC, self.ECFM_process)
        if(self.Results.Config.parallel and not self.Results.Config.batch):
            while(not wx.Process.Exists(self.ECFM_process.GetPid())):
                sleep(0.25)
            os.system("renice -n 10 -p " + "{0:d}".format(self.ECFM_process.GetPid()))
        self.KillECFMButton.Enable()
#        print InvokeECFM + EOLCHART
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('ECFM has launched - please wait.')
        self.GetEventHandler().ProcessEvent(evt)


    def OnUpdate(self, evt):
        self.ECFM_results = evt.data
        if(evt.data is not None):
            self.Results.Config = evt.data.Config
        else:
            self.Results.Config = evt.Config
        evt_out = UpdateConfigEvt(Unbound_EVT_UPDATE_CONFIG, self.GetId())
        self.GetEventHandler().ProcessEvent(evt_out)
        self.ExporttoMatButton.Enable()
        print("Updated main results")

    def OnImportMat(self, evt):
        self.ECFM_results = ECFMResults()
        self.Config = self.ECFM_results.from_mat_file(evt.filename)
        evt_out = UpdateConfigEvt(Unbound_EVT_UPDATE_CONFIG, self.GetId())
        self.GetEventHandler().ProcessEvent(evt_out)
        evt_out_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
        evt_out_2.SetData(self.ECFM_results)
        evt_out_2.SetConfig(self.Config)
        self.Calib_Panel.GetEventHandler().ProcessEvent(evt_out_2)
        self.Scenario_Select_Panel.GetEventHandler().ProcessEvent(evt_out_2)
        self.Plot_Panel.GetEventHandler().ProcessEvent(evt_out_2)
        print("Successfully imported:", evt.filename)

    def OnExporttoMat(self, evt):
        try:
            if(self.ECFM_results is not None):
                self.ECFM_results.to_mat_file()
        except AttributeError as e:
            print("No results to save")
            print(e)

    def OnLockExport(self, evt):
        self.ExporttoMatButton.Disable()

#    def OnExporttoNssf(self, evt):
#        # Output for IDA_GUI with ECFM extension
#        path = "/ptmp1/work/sdenk/nssf/"
#        comment_dialogue = wx.TextEntryDialog(None, 'Please type comment for new edition:')
#        if(comment_dialogue.ShowModal() == wx.ID_OK):
#            comment = comment_dialogue.GetValue()
#        else:
#            print("Export aborted")
#            return
#        ecfm_data_path = os.path.join(path, str(self.Config.shot))
#        if(not os.path.isdir(ecfm_data_path)):
#            os.mkdir(ecfm_data_path)
#        ecfm_data_path = os.path.join(ecfm_data_path, "{0:1.2f}".format(self.time[self.index - 1]))
#        if(not os.path.isdir(ecfm_data_path)):
#            os.mkdir(ecfm_data_path)
#        ecfm_data_path = os.path.join(ecfm_data_path, "OERT")
#        if(not os.path.isdir(ecfm_data_path)):
#            os.mkdir(ecfm_data_path)
#        ed = 0
#        if(os.path.isdir(os.path.join(ecfm_data_path, "ecfm_data"))):
#            editions = glob.glob(os.path.join(ecfm_data_path, "ed*"))
#            for edition in editions:
#                ed_new = int(edition.rsplit(os.sep, 1)[1].rsplit("_", 1)[1])
#                if(ed_new > ed):
#                    ed = ed_new
#            ed += 1
#        if(ed > 0):
#            ecfm_data_path = os.path.join(ecfm_data_path, "ed_{0:d}".format(ed))
#            if(not os.path.isdir(ecfm_data_path)):
#                os.mkdir(ecfm_data_path)
#        ida_log = open(os.path.join(ecfm_data_path, "ida.log"), "w")
#        ida_log.write("{0:1.8f}\n".format(self.Config.time[-1]))
#        ida_log.write("{0:d}\n".format(self.Config.IDA_ed))
#        ida_log.write("{0:s}\n".format(self.Config.EQ_exp))
#        ida_log.write("{0:s}\n".format(self.Config.EQ_diag))
#        ida_log.write("{0:d}\n".format(self.Config.EQ_ed))
#        if("ECE" in self.Config.used_diags_dict.keys() and not self.Config.Ext_plasma):
#            ida_log.write("{0:s}\n".format(self.Config.used_diags_dict["ECE"].exp))
#            ida_log.write("{0:s}\n".format(self.Config.used_diags_dict["ECE"].diag))
#            ida_log.write("{0:d}\n".format(self.Config.used_diags_dict["ECE"].ed))
#        else:
#            ida_log.write("{0:s}\n".format("AUGD"))
#            ida_log.write("{0:s}\n".format("RMD"))
#            ida_log.write("{0:d}\n".format(0))
#        ida_log.write("{0:1.8f}\n".format(self.Config.Te_rhop_scale))
#        ida_log.write("{0:1.8f}\n".format(1.0))
#        ida_log.write("{0:1.8f}\n".format(self.Config.plasma_dict["RwallX"]))
#        ida_log.write("{0:1.8f}".format(self.Config.plasma_dict["RwallO"]))
#        ida_log.flush()
#        ida_log.close()
#        try:
#            if(not os.path.isdir(os.path.join(ecfm_data_path, "ecfm_data"))):
#                shutil.copytree(os.path.join(self.Config.working_dir, "ecfm_data"), os.path.join(ecfm_data_path, "ecfm_data"))
#            else:
#                root_src_dir = os.path.join(self.Config.working_dir, "ecfm_data")
#                root_target_dir = os.path.join(ecfm_data_path, "ecfm_data")
#                for src_dir, dirs, files in os.walk(root_src_dir):
#                    dst_dir = src_dir.replace(root_src_dir, root_target_dir)
#                    if not os.path.exists(dst_dir):
#                        os.mkdir(dst_dir)
#                    for file_ in files:
#                        src_file = os.path.join(src_dir, file_)
#                        dst_file = os.path.join(dst_dir, file_)
#                        if os.path.exists(dst_file):
#                            os.remove(dst_file)
#                        if(os.path.isfile(src_file)):
#                            shutil.copyfile(src_file, dst_dir)
#            comment_file = open(os.path.join(ecfm_data_path, "ecfm_data", "comment"), "w")
#            comment_file.write(comment)
#            comment_file.flush()
#            comment_file.close()
#        except shutil.Error as e:
#            print("Error during copying of ecfm_data")
#            print(e)
#            return

#    def OnExporttotokpNssf(self, evt):
#        # Output for IDA_GUI with ECFM extension
#        path = "/tokp/work/sdenk/nssf/"
#        comment_dialogue = wx.TextEntryDialog(None, 'Please type comment for new edition:')
#        if(comment_dialogue.ShowModal() == wx.ID_OK):
#            comment = comment_dialogue.GetValue()
#        else:
#            print("Export aborted")
#            return
#        ecfm_data_path = os.path.join(path, str(self.Config.shot))
#        if(not os.path.isdir(ecfm_data_path)):
#            os.mkdir(ecfm_data_path)
#        ecfm_data_path = os.path.join(ecfm_data_path, "{0:1.2f}".format(self.time[self.index - 1]))
#        if(not os.path.isdir(ecfm_data_path)):
#            os.mkdir(ecfm_data_path)
#        ecfm_data_path = os.path.join(ecfm_data_path, "OERT")
#        if(not os.path.isdir(ecfm_data_path)):
#            os.mkdir(ecfm_data_path)
#        ed = 0
#        if(os.path.isdir(os.path.join(ecfm_data_path, "ecfm_data"))):
#            editions = glob.glob(os.path.join(ecfm_data_path, "ed*"))
#            for edition in editions:
#                ed_new = int(edition.rsplit(os.sep, 1)[1].rsplit("_", 1)[1])
#                if(ed_new > ed):
#                    ed = ed_new
#            ed += 1
#        if(ed > 0):
#            ecfm_data_path = os.path.join(ecfm_data_path, "ed_{0:d}".format(ed))
#            if(not os.path.isdir(ecfm_data_path)):
#                os.mkdir(ecfm_data_path)
#        ida_log = open(os.path.join(ecfm_data_path, "ida.log"), "w")
#        ida_log.write("{0:1.8f}\n".format(self.Config.time[-1]))
#        ida_log.write("{0:d}\n".format(self.Config.IDA_ed))
#        ida_log.write("{0:s}\n".format(self.Config.EQ_exp))
#        ida_log.write("{0:s}\n".format(self.Config.EQ_diag))
#        ida_log.write("{0:d}\n".format(self.Config.EQ_ed))
#        if("ECE" in self.Config.used_diags_dict.keys() and not self.Config.Ext_plasma):
#            ida_log.write("{0:s}\n".format(self.Config.used_diags_dict["ECE"].exp))
#            ida_log.write("{0:s}\n".format(self.Config.used_diags_dict["ECE"].diag))
#            ida_log.write("{0:d}\n".format(self.Config.used_diags_dict["ECE"].ed))
#        else:
#            ida_log.write("{0:s}\n".format("AUGD"))
#            ida_log.write("{0:s}\n".format("RMD"))
#            ida_log.write("{0:d}\n".format(0))
#        ida_log.write("{0:1.8f}\n".format(self.Config.Te_rhop_scale))
#        ida_log.write("{0:1.8f}\n".format(1.0))
#        ida_log.write("{0:1.8f}\n".format(self.Config.plasma_dict["RwallX"]))
#        ida_log.write("{0:1.8f}".format(self.Config.plasma_dict["RwallO"]))
#        ida_log.flush()
#        ida_log.close()
#        try:
#            if(not os.path.isdir(os.path.join(ecfm_data_path, "ecfm_data"))):
#                shutil.copytree(os.path.join(self.Config.working_dir, "ecfm_data"), os.path.join(ecfm_data_path, "ecfm_data"))
#            else:
#                root_src_dir = os.path.join(self.Config.working_dir, "ecfm_data")
#                root_target_dir = os.path.join(ecfm_data_path, "ecfm_data")
#                for src_dir, dirs, files in os.walk(root_src_dir):
#                    dst_dir = src_dir.replace(root_src_dir, root_target_dir)
#                    if not os.path.exists(dst_dir):
#                        os.mkdir(dst_dir)
#                    for file_ in files:
#                        src_file = os.path.join(src_dir, file_)
#                        dst_file = os.path.join(dst_dir, file_)
#                        if os.path.exists(dst_file):
#                            os.remove(dst_file)
#                        if(os.path.isfile(src_file)):
#                            shutil.copyfile(src_file, dst_dir)
#            comment_file = open(os.path.join(ecfm_data_path, "ecfm_data", "comment"), "w")
#            comment_file.write(comment)
#            comment_file.flush()
#            comment_file.close()
#        except shutil.Error as e:
#            print("Error during copying of ecfm_data")
#            print(e)
#            return

    def OnNextTimeStep(self, evt):
        if(not self.stop_current_evaluation):
            self.ProcessTimeStep()
        else:
            self.time = self.time[0:self.index]  # shorten time array in case of early termination
            self.Config.time = self.time
            self.ECFM_results.tidy_up()
            self.ExporttoMatButton.Enable()
            evt_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
            evt_2.SetData(self.ECFM_results)
            evt_2.SetConfig(self.Config)
            self.Calib_Panel.GetEventHandler().ProcessEvent(evt_2)
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('ECFM has Finished!')
            self.Progress_label.SetLabel("No ECFM run in progress")
            self.ProgressBar.SetValue(0)
            self.sizer.Layout()
            self.StartECFMButton.Enable()

    def OnKillECFM(self, evt):
        self.stop_current_evaluation = True
        print("Waiting for current calculation to finish")
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Termination scheduled - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        self.KillECFMButton.Disable()

    def OnIdle(self, evt):
        if self.ECFM_process is not None:
            stream = self.ECFM_process.GetInputStream()
            if stream is not None:
                if stream.CanRead():
                    text = stream.read()
                    self.Log_Box.AppendText(text)
            evt.RequestMore()

    def OnProcessEnded(self, evt):
        if(self.ECFM_process is None):
            print("ECFM model has crashed")
            print("Please read Error log above")
            self.ECFM_results = ECFMResults()
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('ECFM has crashed - sorry!')
            self.Progress_label.SetLabel("No ECFM run in progress")
            self.StartECFMButton.Enable()
            self.GetEventHandler().ProcessEvent(evt)
            return
        stream = self.ECFM_process.GetInputStream()
        if stream is not None:
            if stream.CanRead():
                text = stream.read()
                self.Log_Box.AppendText(text)
        self.ECFM_process.Destroy()
        self.ECFM_process = None
        self.ECFM_pid = None
        self.ECFM_running = False
        try:
            # Append times twice to track which time points really do have results in case of crashes
            self.Results.append_new_results(self.Results.Scenario.plasma_dict["time"][self.index])
            self.index += 1
        except IOError as e:
            print("Results of ECFM cannot be found!")
            print("Most likely cause is an error that occurred within the ECFM")
            print("Please run the ECFM with current input parameters in a separate shell.")
            print("The command to launch the ECFM can be found above.")
            print("Afterwards please send any error messages that appear at sdenk|at|ipp.mpg.de")
            print("If no errors occur make sure that you don't have another instance of ECFM GUI working in the same working directory")
            print(e)
            print("Skipping current time point {0:1.4f} and continuing".format(self.time[self.index]))
            self.time = np.delete(self.time, self.index)
        except IndexError as e:
            print("Error parsing results of ECFM")
            print("Most likely cause is an error that occurred within the ECFM")
            print("Please run the ECFM with current input parameters in a separate shell.")
            print("The command to launch the ECFM can be found above.")
            print("Afterwards please send any error messages that appear at sdenk|at|ipp.mpg.de")
            print("If no errors occur make sure that you don't have another instance of ECFM GUI working in the same working directory")
            print(e)
            self.Progress_label.SetLabel("No ECFM run in progress")
            self.ProgressBar.SetValue(100)
            self.GetEventHandler().ProcessEvent(evt)
            self.Results = ECFMResults()  # Empty results
            self.stop_current_evaluation = True
            return
        if(self.index < len(self.time) and not self.stop_current_evaluation):
            self.Progress_label.SetLabel("ECFM running - ({0:d}/{1:d})".format(self.index + 1, len(self.time)))
            self.sizer.Layout()
            self.ProgressBar.SetValue(int(100.0 * float(self.index) / float(len(self.time))))
            evt = NewStatusEvt(Unbound_EVT_NEXT_TIME_STEP, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)
        else:
            self.time = self.time[0:self.index]  # shorten time array in case of early termination
            if(len(self.time) == 0):
                print("None of the ECFM runs were completed succesfully - sorry")
                self.ECFM_results = ECFMResults()
                self.Progress_label.SetLabel("No ECFM run in progress")
                self.ProgressBar.SetValue(100)
                self.GetEventHandler().ProcessEvent(evt)
                self.ECFM_results = ECFMResults()  # Empty results
                self.stop_current_evaluation = True
                self.StartECFMButton.Enable()
                return
            self.Config.time = np.copy(self.time)
            self.ECFM_results.Config.time = np.copy(self.time)
            self.KillECFMButton.Disable()
            self.stop_current_evaluation = False
            self.ECFM_results.tidy_up()
            self.ExporttoMatButton.Enable()
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('ECFM has Finished!')
            self.Progress_label.SetLabel("No ECFM run in progress")
            self.ProgressBar.SetValue(100)
            self.GetEventHandler().ProcessEvent(evt)
            evt_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
            evt_2.SetData(self.ECFM_results)
            evt_2.SetConfig(self.Config)
            self.Calib_Panel.GetEventHandler().ProcessEvent(evt_2)
            self.Scenario_Select_Panel.GetEventHandler().ProcessEvent(evt_2)
            self.Plot_Panel.GetEventHandler().ProcessEvent(evt_2)
            print("-------- ECFM has terminated -----------\n")
            self.StartECFMButton.Enable()

    def OnConfigLoaded(self, evt):
        self.NotebookPanel.Notebook.DistributeInfo(self.Config, self.time)

class Config_Page(wx.Panel):
    def __init__(self, parent, Config, border=1, maxwidth=max_var_in_row, \
                    parentmode=False, style=wx.TAB_TRAVERSAL | wx.NO_BORDER):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=style)
        self.name = "ECRad settings"
        columns = 8
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.grid_list = []
        self.labels = []
        self.lines = []
        self.lines.append(wx.StaticLine(self, wx.ID_ANY))
        self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
        self.labels.append(wx.StaticText(self, wx.ID_ANY, "ECRad Settings"))
        self.sizer.Add(self.labels[-1], 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.lines.append(wx.StaticLine(self, wx.ID_ANY))
        self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
        self.grid_list.append(wx.GridSizer(0, columns, 0, 0))
        self.dstf_tc = simple_label_tc(self, "dstf", Config.dstf, "string")
        self.grid_list[-1].Add(self.dstf_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.output_cb = simple_label_cb(self, "Extra output", Config.extra_output)
        self.grid_list[-1].Add(self.output_cb, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.raytracing_cb = simple_label_cb(self, "Raytracing", Config.raytracing)
        self.grid_list[-1].Add(self.raytracing_cb, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.ripple_cb = simple_label_cb(self, "Magn. field Ripple", Config.ripple)
        self.grid_list[-1].Add(self.ripple_cb, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.weak_rel_cb = simple_label_cb(self, "Weak rel.", Config.weak_rel)
        self.grid_list[-1].Add(self.weak_rel_cb, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.bt_vac_correction_tc = simple_label_tc(self, "vacuum B_t scale", Config.bt_vac_correction, "real")
        self.grid_list[-1].Add(self.bt_vac_correction_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.N_ray_tc = simple_label_tc(self, "# rays", Config.N_ray, "integer")
        self.grid_list[-1].Add(self.N_ray_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.N_freq_tc = simple_label_tc(self, "# frequencies", Config.N_freq, "integer")
        self.grid_list[-1].Add(self.N_freq_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.ratio_for_third_tc = simple_label_tc(self, "omega_c/omega w. 3rd", Config.ratio_for_3rd_harm, "real")
        self.grid_list[-1].Add(self.ratio_for_third_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.considered_modes_tc = simple_label_tc(self, "Modes to consider", Config.considered_modes, "integer")
        self.grid_list[-1].Add(self.considered_modes_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.mode_conv_tc = simple_label_tc(self, "mode conv. ratio", Config.mode_conv, "real")
        self.grid_list[-1].Add(self.mode_conv_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.reflec_X_tc = simple_label_tc(self, "Wall refl. coeff. X-mode", Config.reflec_X, "real")
        self.grid_list[-1].Add(self.reflec_X_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.reflec_O_tc = simple_label_tc(self, "Wall refl. coeff. O-mode", Config.reflec_O, "real")
        self.grid_list[-1].Add(self.reflec_O_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.sizer.Add(self.grid_list[-1], 0, wx.ALL | wx.LEFT, 5)
        self.lines.append(wx.StaticLine(self, wx.ID_ANY))
        self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
        self.labels.append(wx.StaticText(self, wx.ID_ANY, "Execution Settings"))
        self.sizer.Add(self.labels[-1], 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.lines.append(wx.StaticLine(self, wx.ID_ANY))
        self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
        self.grid_list.append(wx.GridSizer(0, columns, 0, 0))
        self.working_dir_tc = simple_label_tc(self, "Working dir.", Config.working_dir, "string")
        self.grid_list[-1].Add(self.working_dir_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.debug_cb = simple_label_cb(self, "Debug", Config.debug)
        self.grid_list[-1].Add(self.debug_cb, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.batch_cb = simple_label_cb(self, "Batch", Config.batch)
        self.grid_list[-1].Add(self.batch_cb, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.parallel_cb = simple_label_cb(self, "Parallel", Config.parallel)
        self.grid_list[-1].Add(self.parallel_cb, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.parallel_cores_tc = simple_label_tc(self, "# cores", Config.parallel_cores, "integer")
        self.grid_list[-1].Add(self.parallel_cores_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.wall_time_tc = simple_label_tc(self, "wall time [h]", Config.wall_time, "integer")
        self.grid_list[-1].Add(self.wall_time_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.vmem_tc = simple_label_tc(self, "virtual memory [MB]", Config.vmem, "integer")
        self.grid_list[-1].Add(self.vmem_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.max_points_svec_tc = simple_label_tc(self, "Max points on LOS", Config.max_points_svec, "integer")
        self.grid_list[-1].Add(self.max_points_svec_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.sizer.Add(self.grid_list[-1], 0, wx.ALL | wx.LEFT, 5)
        self.lines.append(wx.StaticLine(self, wx.ID_ANY))
        self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
        self.labels.append(wx.StaticText(self, wx.ID_ANY, "Scenario Settings"))
        self.sizer.Add(self.labels[-1], 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.lines.append(wx.StaticLine(self, wx.ID_ANY))
        self.sizer.Add(self.lines[-1], 0, wx.ALL | wx.EXPAND, 5)
        self.grid_list.append(wx.GridSizer(0, columns, 0, 0))
        self.Te_rhop_scale_tc = simple_label_tc(self, "rhop scale for Te", Config.Te_rhop_scale, "real")
        self.grid_list[-1].Add(self.Te_rhop_scale_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.ne_rhop_scale_tc = simple_label_tc(self, "rhop scale for ne", Config.ne_rhop_scale, "real")
        self.grid_list[-1].Add(self.ne_rhop_scale_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.Te_scale_tc = simple_label_tc(self, "Te scale", Config.Te_scale, "real")
        self.grid_list[-1].Add(self.Te_scale_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.ne_scale_tc = simple_label_tc(self, "ne scale", Config.ne_scale, "real")
        self.grid_list[-1].Add(self.ne_scale_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.ds_large_tc = simple_label_tc(self, "Large step size [m]", Config.large_ds, "real")
        self.grid_list[-1].Add(self.ds_large_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.ds_small_tc = simple_label_tc(self, "Small step size [m]", Config.small_ds, "real")
        self.grid_list[-1].Add(self.ds_small_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.R_shift_tc = simple_label_tc(self, "R shift [m]", Config.R_shift, "real")
        self.grid_list[-1].Add(self.R_shift_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.z_shift_tc = simple_label_tc(self, "z shift [m]", Config.z_shift, "real")
        self.grid_list[-1].Add(self.z_shift_tc, 0, wx.ALL | wx.LEFT | wx.TOP, 5)
        self.sizer.Add(self.grid_list[-1], 0, wx.ALL | wx.LEFT, 5)

    def UpdateConfig(self, Config):
        Config.working_dir = self.working_dir_tc.GetValue()
        if(not Config.working_dir.endswith(os.path.sep)):
            Config.working_dir += os.path.sep
        if(not os.path.isdir(Config.working_dir)):
            print("Selected working directory does not exist - please create it")
            print("Chosen directory: " + Config.working_dir)
            raise IOError("Please specify an existing directory as working directory")
        Config.dstf = self.dstf_tc.GetValue()
        Config.extra_output = self.output_cb.GetValue()
        Config.debug = self.debug_cb.GetValue()
        Config.batch = self.batch_cb.GetValue()
        Config.parallel = self.parallel_cb.GetValue()
        Config.parallel_cores = self.parallel_cores_tc.GetValue()
        Config.wall_time = self.wall_time_tc.GetValue()
        Config.vmem = self.vmem_tc.GetValue()
        Config.raytracing = self.raytracing_cb.GetValue()
        Config.ripple = self.ripple_cb.GetValue()
        Config.weak_rel = self.weak_rel_cb.GetValue()
        Config.bt_vac_correction = self.bt_vac_correction_tc.GetValue()
        Config.N_ray = self.N_ray_tc.GetValue()
        Config.N_freq = self.N_freq_tc.GetValue()
        Config.ratio_for_3rd_harm = self.ratio_for_third_tc.GetValue()
        Config.considered_modes = self.considered_modes_tc.GetValue()
        Config.mode_conv = self.mode_conv_tc.GetValue()
        Config.Te_rhop_scale = self.Te_rhop_scale_tc.GetValue()
        Config.ne_rhop_scale = self.ne_rhop_scale_tc.GetValue()
        Config.reflec_X = self.reflec_X_tc.GetValue()
        Config.reflec_O = self.reflec_O_tc.GetValue()
        Config.Te_scale = self.Te_scale_tc.GetValue()
        Config.ne_scale = self.ne_scale_tc.GetValue()
        Config.large_ds = self.ds_large_tc.GetValue()
        Config.small_ds = self.ds_small_tc.GetValue()
        Config.max_points_svec = self.max_points_svec_tc.GetValue()
        Config.R_shift = self.R_shift_tc.GetValue()
        Config.z_shift = self.z_shift_tc.GetValue()
        return Config

    def SetConfig(self, Config):
        self.working_dir_tc.SetValue(Config.working_dir)
        self.dstf_tc.SetValue(Config.dstf)
        self.output_cb.SetValue(Config.extra_output)
        self.debug_cb.SetValue(Config.debug)
        self.batch_cb.SetValue(Config.batch)
        self.parallel_cb.SetValue(Config.parallel)
        self.parallel_cores_tc.SetValue(Config.parallel_cores)
        self.wall_time_tc.SetValue(Config.wall_time)
        self.vmem_tc.SetValue(Config.vmem)
        self.raytracing_cb.SetValue(Config.raytracing)
        self.ripple_cb.SetValue(Config.ripple)
        self.weak_rel_cb.SetValue(Config.weak_rel)
        self.bt_vac_correction_tc.SetValue(Config.bt_vac_correction)
        self.N_ray_tc.SetValue(Config.N_ray)
        self.N_freq_tc.SetValue(Config.N_freq)
        self.ratio_for_third_tc.SetValue(Config.ratio_for_3rd_harm)
        self.considered_modes_tc.SetValue(Config.considered_modes)
        self.mode_conv_tc.SetValue(Config.mode_conv)
        self.Te_rhop_scale_tc.SetValue(Config.Te_rhop_scale)
        self.ne_rhop_scale_tc.SetValue(Config.ne_rhop_scale)
        self.reflec_X_tc.SetValue(Config.reflec_X)
        self.reflec_O_tc.SetValue(Config.reflec_O)
        self.Te_scale_tc.SetValue(Config.Te_scale)
        self.ne_scale_tc.SetValue(Config.ne_scale)
        self.ds_large_tc.SetValue(Config.large_ds)
        self.ds_small_tc.SetValue(Config.small_ds)
        self.max_points_svec_tc.SetValue(Config.max_points_svec)
        self.R_shift_tc.SetValue(Config.R_shift)
        self.z_shift_tc.SetValue(Config.z_shift)





class CalibPanel(wx.Panel):
    def __init__(self, parent, Scenario):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.fig = plt.figure(figsize=(8.5, 6.5), tight_layout=False)
        self.dummy_fig = plt.figure(figsize=(4.5, 4.5), tight_layout=False)
        self.fig.clf()
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.UpdateCoords)
        self.results = None
        self.cur_diag = None
        self.Bind(wx.EVT_ENTER_WINDOW, self.ChangeCursor)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.canvas.draw()
        self.pc_obj = plotting_core(self.fig, self.dummy_fig, False)
        self.plot_toolbar = NavigationToolbar2Wx(self.canvas)
        self.canvas_sizer = wx.BoxSizer(wx.VERTICAL)
        tw, th = self.plot_toolbar.GetSize().Get()
        fw, fh = self.plot_toolbar.GetSize().Get()
        self.plot_toolbar.SetSize(wx.Size(fw, th))
        self.plot_toolbar.Realize()
        self.plotted_time_points = []  # To avoid duplicates
        self.button_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.calibrate_button = wx.Button(self, 0, "Calibrate")
        self.calibrate_button.Bind(wx.EVT_BUTTON, self.OnCalibrate)
        self.plot_avg_button = wx.Button(self, 0, "Plot avg.")
        self.plot_avg_button.Bind(wx.EVT_BUTTON, self.OnPlotAvg)
        if(Phoenix):
            self.plot_avg_button.SetToolTip("Plot avg. calib factors once they are loaded")
        else:
            self.plot_avg_button.SetToolTipString("Plot avg. calib factors once they are loaded")
        self.reset_plot_button = wx.Button(self, 0, "Reset Plot")
        self.reset_plot_button.Bind(wx.EVT_BUTTON, self.OnResetPlot)
        self.button_sizer.Add(self.calibrate_button, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.button_sizer.Add(self.plot_avg_button, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.button_sizer.Add(self.reset_plot_button, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.button_ctrl_sizer.Add(self.button_sizer, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.control_sizer = wx.GridSizer(0, 5, 0, 0)
        self.diag_tc = simple_label_tc(self, "diag", Scenario.default_diag, "string")
        self.control_sizer.Add(self.diag_tc, 0, wx.ALL, 5)
        self.exp_tc = simple_label_tc(self, "exp", "AUGD", "string")
        self.control_sizer.Add(self.exp_tc, 0, wx.ALL, 5)
        self.ed_tc = simple_label_tc(self, "ed", 0, "integer")
        self.control_sizer.Add(self.ed_tc, 0, wx.ALL, 5)
        self.smoothing_tc = simple_label_tc(self, "binning [ms]", 1.0, "real")
        self.control_sizer.Add(self.smoothing_tc, 0, wx.ALL, 5)
        self.overwrite_diag_cb = simple_label_cb(self, "overwrite diag", False)
        self.control_sizer.Add(self.overwrite_diag_cb, 0, wx.ALL, 5)
        self.button_ctrl_sizer.Add(self.control_sizer, 0, \
                wx.ALIGN_LEFT, 0)
        self.line1 = wx.StaticLine(self, wx.ID_ANY)
        self.button_ctrl_sizer.Add(self.line1, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.timepoint_label = wx.StaticText(self, wx.ID_ANY, \
                                             "Run calibrate once with all time points. " + \
                                             "Afterwards refine calibration by double clicking " + \
                                             "time points and reviewing the calibration", style=wx.ALIGN_CENTER_HORIZONTAL)
        self.timepoint_label.Wrap(400)
        self.timepoint_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.timepoint_label_sizer.AddStretchSpacer(1)
        self.timepoint_label_sizer.Add(self.timepoint_label, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.timepoint_label_sizer.AddStretchSpacer(1)
        self.button_ctrl_sizer.Add(self.timepoint_label_sizer, 0, \
                         wx.ALIGN_CENTER | wx.ALL, 5)
        self.line2 = wx.StaticLine(self, wx.ID_ANY)
        self.button_ctrl_sizer.Add(self.line2, 0, \
                         wx.EXPAND | wx.ALL, 5)
        self.used = []
        self.unused = []
        self.select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.used_sizer = wx.BoxSizer(wx.VERTICAL)
        self.used_text = wx.StaticText(self, wx.ID_ANY, "Used time points")
        self.used_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.used_list.AppendItems(self.used)
        self.used_list.Bind(wx.EVT_LISTBOX_DCLICK, self.OnPlotUsedTimePoint)
        self.used_sizer.Add(self.used_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.used_sizer.Add(self.used_list, 1, wx.ALL | wx.EXPAND, 5)
        self.RemoveButton = wx.Button(self, wx.ID_ANY, '>>')
        self.RemoveButton.Bind(wx.EVT_BUTTON, self.OnRemoveSelection)
        self.AddButton = wx.Button(self, wx.ID_ANY, '<<')
        self.AddButton.Bind(wx.EVT_BUTTON, self.OnAddSelection)
        self.select_button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.select_button_sizer.Add(self.RemoveButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.select_button_sizer.Add(self.AddButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer = wx.BoxSizer(wx.VERTICAL)
        self.unused_text = wx.StaticText(self, wx.ID_ANY, "Unused time points")
        self.unused_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.unused_list.Bind(wx.EVT_LISTBOX_DCLICK, self.OnPlotUnUsedTimePoint)
        self.unused_sizer.Add(self.unused_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer.Add(self.unused_list, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.used_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.select_button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        self.select_sizer.Add(self.unused_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.button_ctrl_sizer.Add(self.select_sizer, 1, \
                         wx.EXPAND | wx.ALL, 5)
        self.canvas_sizer.Add(self.plot_toolbar, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.canvas_sizer.Add(self.canvas, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.sizer.Add(self.button_ctrl_sizer, 1, wx.ALL | \
                wx.EXPAND, 5)
        self.sizer.Add(self.canvas_sizer, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)

    def OnUpdate(self, evt):
        self.shot_tc.SetValue(str(evt.Config.shot))
        self.shot = evt.Config.shot
        self.Config = evt.Config
        self.Results = evt.data
        self.time = self.Results.Config.time
        diag_name_list = []
        for key in self.Config.used_diags_dict.keys():
            diag_name_list.append(self.Config.used_diags_dict[key].name)
        if(self.diag_tc.GetValue() not in diag_name_list):
            i = 0
            while(diag_name_list[i] == "RMD" or diag_name_list[i] == "CEC"):
                i += 1
                if(i >= len(diag_name_list)):
                    break
            if(i < len(diag_name_list)):
                self.diag_tc.SetValue(diag_name_list[i])
                self.cur_diag = self.Config.used_diags_dict[diag_name_list[i]]
            elif(self.cur_diag is None):
                print("Warning no diagnostic found that requires cross calibration")
                return
        else:
            self.cur_diag = self.Config.used_diags_dict[self.diag_tc.GetValue()]
        if(self.cur_diag.name in self.Results.masked_time_points.keys()):
            self.used = list(self.time[self.Results.masked_time_points[self.cur_diag.name]].astype("|S7"))
            self.unused = list(self.time[self.Results.masked_time_points[self.cur_diag.name] == False].astype("|S7"))
        else:
            self.used = list(self.time.astype("|S7"))
            self.unused = []
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)


    def OnAddSelection(self, evt):
        sel = self.unused_list.GetSelections()
        for i_sel in sel:
            string = self.unused_list.GetString(i_sel)
            self.used.append(self.unused.pop(self.unused.index(string)))
        self.used = list(set(self.used))
        self.used.sort()
        self.unused = list(set(self.unused))
        self.unused.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def OnRemoveSelection(self, evt):
        sel = self.used_list.GetSelections()
        for i_sel in sel:
            string = self.used_list.GetString(i_sel)
            self.unused.append(self.used.pop(self.used.index(string)))
        self.used = list(set(self.used))
        self.used.sort()
        self.unused = list(set(self.unused))
        self.unused.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def ChangeCursor(self, event):
        if(Phoenix):
            self.canvas.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        else:
            self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

    def UpdateCoords(self, event):
        if event.inaxes:
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            x, y = event.xdata, event.ydata
            evt.SetStatus('x = {0:1.3e}: y = {1:1.3e}'.format(x, y))
            self.GetEventHandler().ProcessEvent(evt)

    def OnCalibrate(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Calibrating - GUI might be unresponsive for minutes - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        diag_name = self.diag_tc.GetValue()
        use_EXT = False
        try:
            for key in self.Config.used_diags_dict.keys():
                if(key == diag_name):
                    self.cur_diag = self.Config.used_diags_dict[key]
                elif(self.overwrite_diag_cb.GetValue() and key == "EXT"):
                    self.cur_diag = DefaultDiagDict[diag_name]
                    self.cur_diag.name = self.diag_tc.GetValue()
                    self.cur_diag.diag = self.cur_diag.name
                    self.cur_diag.exp = self.exp_tc.GetValue()
                    self.cur_diag.ed = self.ed_tc.GetValue()
                    self.cur_diag.t_smooth = self.smoothing_tc.GetValue() * 1.e-3
                    self.Config.used_diags_dict[self.cur_diag.name] = self.cur_diag
                    self.Results.diag[self.Results.diag == "EXT"] = self.cur_diag.name
                    del(self.Config.used_diags_dict[key])
        except AttributeError:
            print("ERROR! Nothing to calibrate!")
            return
        if(self.cur_diag is None):
            print("Could not find any data for in current ECFM data set", diag_name)
            print("Available diagnostics are", self.Config.used_diags_dict.keys())
            return
        exp = self.exp_tc.GetValue()
        if(exp != self.cur_diag.exp):
            print("Warning experiment of diagnostic not consistent with ECFM configuration")
            print("Proceeding anyways")
            self.cur_diag.exp = exp
        ed = int(self.ed_tc.GetValue())
        if(exp != self.cur_diag.ed):
            print("Warning edition of diagnostic not consistent with ECFM configuration")
            print("Proceeding anyways")
            self.cur_diag.ed = ed
        smoothing = self.smoothing_tc.GetValue()
        masked_timepoints = np.zeros(len(self.Results.Config.time), np.bool)
        masked_timepoints[:] = True
        self.delta_t = 0.5 * np.mean(self.Results.Config.time[1:len(self.Results.Config.time)] - \
                                     self.Results.Config.time[0:len(self.Results.Config.time) - 1])
        no_double_booking = []
        for i in range(len(self.unused)):
            j = np.argmin(np.abs(self.Results.Config.time - float(self.unused[i])))  # To avoid round off errors
            if(j not in no_double_booking):
                # this should identify the masked time points reliably
                masked_timepoints[j] = False
                no_double_booking.append(j)
            else:
                print("Attempted double booking", float(self.unused[i]), self.Results.Config.time[j])
                return
        if(len(self.Results.Config.time[masked_timepoints]) != len(self.used)):
            print("Error: Not as many masked time points as used time points")
            print("Recheck selection criterion")
            return
        self.pc_obj.reset(False)
#        try:
#        if("O" in self.Results.modes and self.Results.dstf == "TB"):
#            print("Using Gray Trad for calibration")
#            calib_mat, std_dev_mat, calib, rel_dev = calibrate(self.shot, self.Results.Config.time[masked_timepoints], \
#                                                 self.Results.Trad_comp[masked_timepoints].T[self.Results.diag == self.cur_diag.name].T, self.cur_diag, \
#                                                 smoothing)
#        else:
        print("Using standard Trad for calibration")
        calib_mat, std_dev_mat, calib, rel_dev, sys_dev = calibrate(self.shot, self.Results.Config.time[masked_timepoints], \
                                         self.Results.Trad[masked_timepoints].T[self.Results.diag == self.cur_diag.name].T, self.cur_diag, \
                                         smoothing)
        if(len(calib) == 0):
            return
#        except ValueError as e:
#            print(e)
#            return
        self.Results.UpdateCalib(self.cur_diag, calib, calib_mat, std_dev_mat, rel_dev, sys_dev, masked_timepoints)
        evt = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
        evt.SetData(self.Results)
        evt.SetConfig(self.Config)
        self.Parent.Parent.GetEventHandler().ProcessEvent(evt)
        freq = get_freqs(self.Config.shot, self.cur_diag)  # * 1.e-9
        self.fig, self.fig_extra = self.pc_obj.diag_calib_avg(self.cur_diag, freq, \
                                   calib, rel_dev, "Avg. calibration factors for diagn. " + self.cur_diag.name)
        self.canvas.draw()
        ed = 1
        filename_out = os.path.join(self.Config.working_dir, "calib_" + str(self.Config.shot) + "_" + self.cur_diag.name + "_ed_" + str(ed))
        while(os.path.exists(filename_out + ".cal")):
            ed += 1
            filename_out = os.path.join(self.Config.working_dir, "calib_" + str(self.Config.shot) + "_" + self.cur_diag.name + "_ed_" + str(ed))
        Calib_Log_File = open(filename_out + ".log", "w")
        Calib_Log_File.write("# " + str(self.Config.shot) + os.linesep)
        if(self.Results.Config.extra_output):
            for time_index in range(len(self.Results.Config.time[masked_timepoints])):
                Calib_Log_File.write("time =  " + "{0:1.2f}\t".format(self.Results.Config.time[masked_timepoints][time_index]) + " s" + os.linesep)
                Calib_Log_File.write("f [Ghz]    rho_cold  c [keV / Vs] R_cold [m] z_cold [m]  R_kin [m]  z_kin [m]        tau" + os.linesep)
                ch_cnt = len(freq)
                for ch in range(ch_cnt):
                    Calib_Log_File.write("{0:3.2f}".format(freq[ch] / 1.e9))
                    for i in range(3):
                        Calib_Log_File.write(" ")
                    Calib_Log_File.write("{0: 1.3e}".format(self.Results.resonance["rhop_cold"][masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch]))
                    for i in range(4):
                        Calib_Log_File.write(" ")
                    Calib_Log_File.write("{0: 1.3e} ".format(calib_mat[time_index][ch ]))
                    Calib_Log_File.write("{0: 1.3e} {1: 1.3e} {2: 1.3e} {3: 1.3e} {4: 1.3e}".format(\
                                        self.Results.resonance["R_cold"][masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch], \
                                        self.Results.resonance["z_cold"][masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch], \
                                        self.Results.resonance["R_warm"][masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch], \
                                        self.Results.resonance["z_warm"][masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch], \
                                        self.Results.tau[masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch]) + os.linesep)
            Calib_Log_File.flush()
            Calib_Log_File.close()
            Calib_File = open(filename_out + ".cal", "w")
            Calib_File.write("# " + str(self.Config.shot) + os.linesep)
            Calib_File.write("f [Ghz]  c [keV / Vs] rel. std. dev [%] R_cold [m] z_cold [m]  R_kin [m]  z_kin [m]        tau" + os.linesep)
            for ch in range(ch_cnt):
                Calib_File.write("{0:3.2f}".format(freq[ch] / 1.e9))
                Calib_File.write("     {0: 1.3e}         {1: 2.2e} {2: 2.2e} ".format(calib[ch], rel_dev[ch], sys_dev[ch]))
                Calib_File.write("{0: 1.3e} {1: 1.3e} {2: 1.3e} {3: 1.3e} {4: 1.3e}".format(\
                                  np.average(self.Results.resonance["R_cold"][masked_timepoints], axis=0)[self.Results.diag == self.cur_diag.name][ch], \
                                  np.average(self.Results.resonance["z_cold"][masked_timepoints], axis=0)[self.Results.diag == self.cur_diag.name][ch], \
                                  np.average(self.Results.resonance["R_warm"][masked_timepoints], axis=0)[self.Results.diag == self.cur_diag.name][ch], \
                                  np.average(self.Results.resonance["z_warm"][masked_timepoints], axis=0)[self.Results.diag == self.cur_diag.name][ch], \
                                  np.average(self.Results.tau[masked_timepoints], axis=0)[self.Results.diag == self.cur_diag.name][ch]) + os.linesep)
            Calib_File.flush()
            Calib_File.close()
        else:
            for time_index in range(len(self.Results.Config.time[masked_timepoints])):
                Calib_Log_File.write("time =  " + "{0:1.2f}\t".format(self.Results.Config.time[masked_timepoints][time_index]) + " s" + os.linesep)
                Calib_Log_File.write("f [Ghz]    rho_cold  c [keV / Vs] R_cold [m] z_cold [m]  R_kin [m]  z_kin [m]        tau" + os.linesep)
                ch_cnt = len(freq)
                for ch in range(ch_cnt):
                    Calib_Log_File.write("{0:3.2f}".format(freq[ch] / 1.e9))
                    for i in range(3):
                        Calib_Log_File.write(" ")
                    Calib_Log_File.write("{0: 1.3e}".format(self.Results.resonance["rhop_cold"][masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch]))
                    for i in range(4):
                        Calib_Log_File.write(" ")
                    Calib_Log_File.write("{0: 1.3e} ".format(calib_mat[time_index][ch ]))
                    Calib_Log_File.write("{0: 1.3e} {1: 1.3e} {2: 1.3e} {3: 1.3e} {4: 1.3e}".format(\
                                        self.Results.resonance["R_cold"][masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch], \
                                        self.Results.resonance["z_cold"][masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch], \
                                        - 1.e0, \
                                        - 1.e0, \
                                        self.Results.tau[masked_timepoints][time_index][self.Results.diag == self.cur_diag.name][ch]) + os.linesep)
            Calib_Log_File.flush()
            Calib_Log_File.close()
            Calib_File = open(filename_out + ".cal", "w")
            Calib_File.write("# " + str(self.Config.shot) + os.linesep)
            Calib_File.write("f [Ghz]  c [keV / Vs] rel. std. dev [%] sys. dev [%] R_cold [m] z_cold [m]  R_kin [m]  z_kin [m]        tau" + os.linesep)
            for ch in range(ch_cnt):
                Calib_File.write("{0:3.2f}".format(freq[ch] / 1.e9))
                Calib_File.write("     {0: 1.3e}         {1: 2.2e} {2: 2.2e} ".format(calib[ch], rel_dev[ch], sys_dev[ch]))
                Calib_File.write("{0: 1.3e} {1: 1.3e} {2: 1.3e} {3: 1.3e} {4: 1.3e}".format(\
                                  np.average(self.Results.resonance["R_cold"][masked_timepoints], axis=0)[self.Results.diag == self.cur_diag.name][ch], \
                                  np.average(self.Results.resonance["z_cold"][masked_timepoints], axis=0)[self.Results.diag == self.cur_diag.name][ch], \
                                  - 1.e0, \
                                  - 1.e0, \
                                  np.average(self.Results.tau[masked_timepoints], axis=0)[self.Results.diag == self.cur_diag.name][ch]) + os.linesep)
            Calib_File.flush()
            Calib_File.close()

    def OnPlotAvg(self, evt):
        if("avg" not in self.plotted_time_points):
            if(self.cur_diag.diag not in self.Results.calib.keys()):
                    print("Error: No calibration data available - calibrate first")
                    return
            self.plotted_time_points.append("avg")
            freq = get_freqs(self.Config.shot, self.cur_diag)
            self.fig, self.fig_extra = self.pc_obj.diag_calib_avg(self.cur_diag, freq, \
                                       self.Results.calib[self.cur_diag.diag], self.Results.rel_dev[self.cur_diag.diag], \
                                       "avg")
            self.canvas.draw()
            evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)

    def OnResetPlot(self, evt):
        self.pc_obj.reset(True)
        self.plotted_time_points = []
        self.fig.clf()
        self.canvas.draw()


    def OnPlotUsedTimePoint(self, evt):
        sel = self.used_list.GetSelections()
        if(len(sel) == 0):
            return
        for i_sel in sel:
            time = float(self.used_list.GetString(i_sel))
            if(time not in self.plotted_time_points):
                if(self.cur_diag.diag not in self.Results.calib_mat.keys()):
                    print("Error: No calibration data available - calibrate first")
                    return
                self.plotted_time_points.append(time)
                index = np.argmin(np.abs(self.Results.Config.time - time))
                freq = get_freqs(self.Config.shot, self.cur_diag)  # * 1.e-9
                self.fig, self.fig_extra = self.pc_obj.diag_calib_slice(self.cur_diag, freq, \
                                           self.Results.calib_mat[self.cur_diag.name][index], self.Results.std_dev_mat[self.cur_diag.name][index], \
                                           "t = {0:2.4f} s".format(self.Results.Config.time[index]))
                self.canvas.draw()
                evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
                self.GetEventHandler().ProcessEvent(evt)

    def OnPlotUnUsedTimePoint(self, evt):
        sel = self.unused_list.GetSelections()
        if(len(sel) == 0):
            return
        for i_sel in sel:
            time = float(self.unused_list.GetString(i_sel))
            if(time not in self.plotted_time_points):
                if(self.cur_diag.diag not in self.Results.calib_mat.keys()):
                    print("Error: No calibration data available - calibrate first")
                    return
                self.plotted_time_points.append(time)
                index = np.argmin(np.abs(self.Results.Config.time - time))
                freq = get_freqs(self.Config.shot, self.cur_diag)  # * 1.e-9
                self.fig, self.fig_extra = self.pc_obj.diag_calib_slice(self.cur_diag, freq, \
                                           self.Results.calib_mat[self.cur_diag.name][index], self.Results.std_dev_mat[self.cur_diag.name][index], \
                                           "t = {0:2.4f} s".format(self.Results.Config.time[index]))
                self.canvas.draw()
                evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
                self.GetEventHandler().ProcessEvent(evt)

class CalibEvolutionPanel(wx.Panel):
    def __init__(self, parent, working_dir):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.working_dir = working_dir
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.fig = plt.figure(figsize=(7.5, 8.5), tight_layout=False)
        self.dummy_fig = plt.figure(figsize=(9, 6.5), tight_layout=False)
        self.fig.clf()
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.UpdateCoords)
        self.results = None
        self.diagnostic = None
        self.ch_cnt = 0
        self.Bind(wx.EVT_ENTER_WINDOW, self.ChangeCursor)
        self.canvas.draw()
        self.pc_obj = plotting_core(self.fig, self.dummy_fig, False)
        self.plot_toolbar = NavigationToolbar2Wx(self.canvas)
        self.canvas_sizer = wx.BoxSizer(wx.VERTICAL)
        tw, th = self.plot_toolbar.GetSize().Get()
        fw, fh = self.plot_toolbar.GetSize().Get()
        self.plot_toolbar.SetSize(wx.Size(fw, th))
        self.plot_toolbar.Realize()
        self.button_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.load_shots_button = wx.Button(self, 0, "Load ECFM data sets")
        self.load_shots_button.Bind(wx.EVT_BUTTON, self.OnOpenOldFiles)
        self.button_sizer.Add(self.load_shots_button, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.plot_button = wx.Button(self, 0, "Plot selected sets")
        self.plot_button.Bind(wx.EVT_BUTTON, self.OnPlot)
        self.button_sizer.Add(self.plot_button, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        # self.button_sizer.AddStretchSpacer(prop = 10)
        self.clear_results_button = wx.Button(self, 0, "Clear all sets")
        self.clear_results_button.Bind(wx.EVT_BUTTON, self.OnClearAllResults)
        self.button_sizer.Add(self.clear_results_button, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.button_ctrl_sizer.Add(self.button_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.canvas_sizer.Add(self.plot_toolbar, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.canvas_sizer.Add(self.canvas, 0, wx.ALL | \
                wx.ALIGN_LEFT, 5)
        self.used = []
        self.unused = []
        self.select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.used_sizer = wx.BoxSizer(wx.VERTICAL)
        self.used_text = wx.StaticText(self, wx.ID_ANY, "Used shots")
        self.used_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.shotlist = []
        self.ECFM_result_list = []
        self.used_sizer.Add(self.used_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.used_sizer.Add(self.used_list, 1, wx.ALL | wx.EXPAND, 5)
        self.select_button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.RemoveButton = wx.Button(self, wx.ID_ANY, '>>')
        self.RemoveButton.Bind(wx.EVT_BUTTON, self.OnRemoveSelection)
        self.AddButton = wx.Button(self, wx.ID_ANY, '<<')
        self.AddButton.Bind(wx.EVT_BUTTON, self.OnAddSelection)
        self.select_button_sizer.Add(self.RemoveButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.select_button_sizer.Add(self.AddButton, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer = wx.BoxSizer(wx.VERTICAL)
        self.unused_text = wx.StaticText(self, wx.ID_ANY, "Unused shots")
        self.unused_list = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE)
        self.unused_sizer.Add(self.unused_text, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.unused_sizer.Add(self.unused_list, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.used_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.select_sizer.Add(self.select_button_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        self.select_sizer.Add(self.unused_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.select_shot_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.select_shot_sizer.Add(self.select_sizer, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.button_ctrl_sizer, 0, wx.ALL | \
                wx.EXPAND, 5)
        self.button_ctrl_sizer.Add(self.select_shot_sizer, 1, \
                wx.EXPAND, 0)
        self.channel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.diagnostic_tc = simple_label_tc(self, "diagnostic", "CTA", "string")
        self.channel_sizer.Add(self.diagnostic_tc, 0, wx.ALL | wx.ALIGN_CENTER)
        self.channel_label_sizer = wx.BoxSizer(wx.VERTICAL)
        self.ch_label = wx.StaticText(self, wx.ID_ANY, "Channel to be plotted")
        self.ch_ch = wx.Choice(self, wx.ID_ANY)
        self.channel_label_sizer.Add(self.ch_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.channel_label_sizer.Add(self.ch_ch, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.channel_sizer.Add(self.channel_label_sizer, 0, wx.ALL | wx.ALIGN_CENTER)
        self.button_ctrl_sizer.Add(self.channel_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.adv_plot_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.plot_button_Trad = wx.Button(self, 0, "Plot againt Trad")
        self.plot_button_Trad.Bind(wx.EVT_BUTTON, self.OnPlotTradvsSignal)
        self.plot_button_launch = wx.Button(self, 0, "Plot againt launch")
        self.plot_button_launch.Bind(wx.EVT_BUTTON, self.OnPlotCalibvsLaunch)
        self.plot_button_comp = wx.Button(self, 0, "Meas. vs. expected")
        self.plot_button_comp.Bind(wx.EVT_BUTTON, self.OnPlotDiagVsTrad)
        self.adv_plot_sizer.Add(self.plot_button_Trad, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.adv_plot_sizer.Add(self.plot_button_launch, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.Trad_comp_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Trad_comp_sizer.Add(self.plot_button_comp, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.ECE_diag_exp_tc = simple_label_tc(self, "exp", "AUGD", "string")
        self.ECE_diag_diag_tc = simple_label_tc(self, "diag", "RMD", "string")
        self.ECE_diag_ed_tc = simple_label_tc(self, "ed", 0, "integer")
        self.Trad_comp_sizer.Add(self.ECE_diag_exp_tc, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.Trad_comp_sizer.Add(self.ECE_diag_diag_tc, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.Trad_comp_sizer.Add(self.ECE_diag_ed_tc, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.button_ctrl_sizer.Add(self.adv_plot_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.button_ctrl_sizer.Add(self.Trad_comp_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.sizer.Add(self.canvas_sizer, 0, wx.ALL | \
                wx.ALIGN_TOP, 5)
        self.SetClientSize(self.GetEffectiveMinSize())

    def OnAddSelection(self, evt):
        sel = self.unused_list.GetSelections()
        for i_sel in sel:
            string = self.unused_list.GetString(i_sel)
            self.used.append(self.unused.pop(self.unused.index(string)))
        self.used = list(set(self.used))
        self.used.sort()
        self.unused = list(set(self.unused))
        self.unused.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def OnRemoveSelection(self, evt):
        sel = self.used_list.GetSelections()
        for i_sel in sel:
            string = self.used_list.GetString(i_sel)
            self.unused.append(self.used.pop(self.used.index(string)))
        self.used = list(set(self.used))
        self.used.sort()
        self.unused = list(set(self.unused))
        self.unused.sort()
        self.used_list.Clear()
        if(len(self.used) > 0):
            self.used_list.AppendItems(self.used)
        self.unused_list.Clear()
        if(len(self.unused) > 0):
            self.unused_list.AppendItems(self.unused)

    def OnOpenOldFiles(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Loading data - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        dlg = wx.FileDialog(\
            self, message="Choose a preexisting calculation(s)", \
            defaultDir=self.working_dir, \
            wildcard=('Matlab files (*.mat)|*.mat'),
            style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if(dlg.ShowModal() == wx.ID_OK):
            self.diagnostic = self.diagnostic_tc.GetValue()
            paths = dlg.GetPaths()
            dlg.Destroy()
            new_results = []
            for path in paths:
                new_results.append(ECFMResults())
                if(new_results[-1].calib_from_mat_file(path) == False):
                    print("Failed to load file at " + path)
                    continue
#                elif("ed{0:d}".format(new_results[-1].edition) not in path):
#                    print("Edition in .mat file does not match filename - distributing new edition according to filename")
#                    new_results[-1].edition = 0
#                    while("ed{0:d}".format(new_results[-1].edition) not in path):
#                        new_results[-1].edition += 1
                # it would be nice to have also Te in this plot, but the mapping is a pain
#                new_results[-1].Config.time, new_results[-1].Config.plasma_dict = load_IDA_data(self.Config.shot, \
#                                    new_results[-1].Config.time, self.Config.IDA_exp, self.Config.IDA_ed)
            if(len(self.ECFM_result_list) == 0):
                self.ECFM_result_list = new_results
                self.shotlist = []
                self.editionlist = []
                ishot = 0
                try:
                    self.ch_cnt = len(self.ECFM_result_list[ishot].calib[self.diagnostic])
                except KeyError:
                    print("Warning!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                      self.ECFM_result_list[ishot].Config.shot, self.ECFM_result_list[ishot].edition))
                    print("Available diagnostics: ", self.ECFM_result_list[ishot].calib.keys())
                if(self.ch_cnt == 0):
                    while(self.ch_cnt == 0):
                        ishot += 1
                        if(ishot == len(self.ECFM_result_list)):
                            print("Error: None of the selected shots holds any information for your selected diagnostic")
                            print("Please double check that the desired diagnostic has been selected")
                            self.ECFM_result_list = []
                            return
                        try:
                            self.ch_cnt = len(self.ECFM_result_list[ishot].calib[self.diagnostic])
                        except KeyError:
                            print("Warning!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                              self.ECFM_result_list[ishot].Config.shot, self.ECFM_result_list[ishot].edition))
                cur_ch_cnt = 0
                for result in self.ECFM_result_list[ishot:len(self.ECFM_result_list)]:
                    try:
                        cur_ch_cnt = len(result.calib[self.diagnostic])
                        if(self.ch_cnt != cur_ch_cnt):
                            print("Warning!! # {0:d} edition {1:d} does not have the same amount of diagnostic channels as the first shot".format(\
                                          result.Config.shot, result.edition))
                            print("To avoid the comparison of pears with apples the affected shots were not added to the list")
                        else:
                            self.shotlist.append(str(result.Config.shot))
                            self.editionlist.append(str(result.edition))
                    except KeyError:
                        print("Warning!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                          result.Config.shot, self.ECFM_result_list[ishot].edition))
                for i in range(len(self.shotlist)):
                    self.used.append(self.shotlist[i] + "_ed_" + self.editionlist[i])
                self.used_list.AppendItems(self.used)
                self.ch_ch.AppendItems(map(str, range(1, self.ch_cnt + 1)))
            else:
                for new_result in new_results:
                    new_result_replaced_old = False
                    for index in range(len(self.ECFM_result_list)):
                        if(new_result.Config.shot == self.ECFM_result_list[index].Config.shot and new_result.edition == self.ECFM_result_list[index].edition):
                            new_result_replaced_old = True
                            try:
                                cur_ch_cnt = len(new_result.calib[self.diagnostic])
                                if(self.ch_cnt != cur_ch_cnt):
                                    print("Warning!! # {0:d} edition {1:d} does not have the same amount of diagnostic channels as the first shot".format(\
                                                  new_result.Config.shot, new_result.edition))
                                    print("To avoid the comparison of pears with apples the affected shots were not added to the list")
                                else:
                                    self.ECFM_result_list[index] = new_result
                            except KeyError:
                                print("Warning!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                                  new_result.Config.shot, new_result.edition))
                            break
                    if(not new_result_replaced_old):
                        try:
                            cur_ch_cnt = len(new_result.calib[self.diagnostic])
                            if(self.ch_cnt != cur_ch_cnt):
                                print("Warning!! # {0:d} edition {1:d} does not have the same amount of diagnostic channels as the first shot".format(\
                                              new_result.Config.shot, new_result.edition))
                                print("To avoid the comparison of pears with apples the affected shots were not added to the list")
                            else:
                                self.ECFM_result_list.append(new_result)
                                self.shotlist.append(str(self.ECFM_result_list[-1].Config.shot))
                                self.editionlist.append(str(self.ECFM_result_list[-1].edition))
                                self.used.append(self.shotlist[-1] + "_ed_" + self.editionlist[-1])
                                self.used_list.Clear()
                                self.used = list(set(self.used))
                                self.used.sort()
                                self.used_list.AppendItems(self.used)
                        except KeyError:
                            print("Error!! # {0:d} edition {1:d} does not have a calibration for the selected diagnostic".format(\
                                              new_result.Config.shot, new_result.edition))
            if(len(self.ch_ch.GetItems()) > 0):
                self.ch_ch.Select(0)


    def OnPlot(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        if(len(self.used) == 0):
            print("Error: No shots marked for plotting!")
            return
        self.pc_obj.reset(True)
        self.fig.clf()
        self.canvas.draw()
        used_results = []
        for result in self.ECFM_result_list:
            if(str(result.Config.shot) + "_ed_" + str(result.edition) in self.used):
                used_results.append(result)
        ch = self.ch_ch.GetSelection()
        if(ch < 0):
            print("Error!!: No channel selected")
            return
        self.fig = self.pc_obj.calib_evolution(self.diagnostic, ch, used_results)
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def OnPlotTradvsSignal(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        if(len(self.used) == 0):
            print("Error: No shots marked for plotting!")
            return
        self.pc_obj.reset(True)
        self.fig.clf()
        self.canvas.draw()
        used_results = []
        if(self.diagnostic == "CTC" or self.diagnostic == "IEC" or self.diagnostic == "CTA"):
            try:
                beamline = self.ECFM_result_list[0].Config.used_diags_dict[self.diagnostic].beamline
            except KeyError:
                print("Failed to get beamliune - if this is an overwritten EXT diag calculation this is expected")
                beamline = 0
        else:
            beamline = 0
        if(beamline > 0):
            pol_ang_list = []
        print("The poloidal angle plot is disabled at the moment")
        beamline = -1
        for result in self.ECFM_result_list:
            if(str(result.Config.shot) + "_ed_" + str(result.edition) in self.used):
                used_results.append(result)
            if(beamline > 0):
                gy = get_ECRH_viewing_angles(result.Config.shot, beamline, self.ECFM_result_list[0].Config.used_diags_dict[self.diagnostic].base_freq_140)
                pol_ang = []
                for t in result.Config.time:
                    pol_ang.append(gy.theta_pol[np.argmin(np.abs(gy.time - t))])
                pol_ang_list.append(np.array(pol_ang))
        ch = self.ch_ch.GetSelection()
        if(ch < 0):
            print("Error!!: No channel selected")
            return
        time_list = []
        diag_data = []
        std_dev_data = []
        dummy_std_dev_calib = np.zeros(len(result.calib[self.diagnostic]))
        dummy_calib = np.zeros(len(result.calib[self.diagnostic]))
        dummy_calib[:] = 1.e0
        calib_diag = used_results[0].Config.used_diags_dict[self.diagnostic]
        popt_list = []
        for result in used_results:
            time_list.append(result.Config.time)
            if(result.Config.extra_output):
                resonances = result.resonance["rhop_warm"]
            else:
                resonances = result.resonance["rhop_cold"]
            std_dev, data = get_data_calib(diag=calib_diag, shot=result.Config.shot, time=result.Config.time[result.masked_time_points[self.diagnostic]], \
                                           eq_exp=result.Config.EQ_exp, eq_diag=result.Config.EQ_diag, eq_ed=result.Config.EQ_ed, \
                                           calib=dummy_calib, \
                                           std_dev_calib=dummy_std_dev_calib, \
                                           ext_resonances=resonances)
            diag_data.append(data[1].T[ch])
            std_dev_data.append(np.copy(std_dev[0].T[ch]))
            popt, perr = make_fit('linear', result.Trad[result.masked_time_points[self.diagnostic]].T[result.diag == self.diagnostic][ch], \
                                  data[1].T[ch], std_dev[0].T[ch], \
                                  [0.0, 1.0 / np.mean(result.calib_mat[self.diagnostic].T[ch])])
            # Largest deviation of calibration coefficient from measurement minus standard deviation of the measurement
            systematic_error = np.sqrt(np.sum((1.0 / popt[1] - (result.Trad[result.masked_time_points[self.diagnostic]].T[result.diag == self.diagnostic][ch] / \
                                                                data[1].T[ch])) ** 2) / \
                                       len(result.Trad[result.masked_time_points[self.diagnostic]].T[result.diag == self.diagnostic][ch]))
            print("Pseudo systematic error [%] and systematic vs. statistical error ", np.abs(systematic_error * popt[1] * 100.0), \
                  np.abs(systematic_error / (perr[1] / popt[1] ** 2)))
            print("Inital relative error:", np.sqrt(perr[1] ** 2 / popt[1] ** 4) * popt[1])
            popt_list.append(popt)
            print("Fit result: U_0 [V], c [keV/V] / error")
            print("{0:1.4f}, {1:1.4f} / {2:1.4f} , {3:1.4f}".format(popt[0], 1.e0 / popt[1], perr[0], np.sqrt(perr[1] ** 2 / popt[1] ** 4)))
            print("Result from calib and std. dev.")
            print("{0:1.4f}, {1:1.4f}".format(result.calib[self.diagnostic][ch], result.rel_dev[self.diagnostic][ch] * result.calib[self.diagnostic][ch] / 100.0))
            Trad0 = popt[0] / popt[1]
            DeltaTrad0 = np.sqrt(perr[0] ** 2 / popt[1] ** 2 + perr[1] ** 2 * popt[0] ** 2 / popt[1] ** 4)
            print("Trad with zero signal and error [keV]:")
            print("{0:1.4f}, {1:1.4f}".format(Trad0, DeltaTrad0))
        if(beamline > 0):
            min_ang = np.inf
            max_ang = -np.inf
            for i in range(len(pol_ang_list)):
                if(np.max(pol_ang_list[i]) > max_ang):
                    max_ang = np.max(pol_ang_list[i])
                if(np.min(pol_ang_list[i]) < min_ang):
                    min_ang = np.min(pol_ang_list[i])
            if(max_ang - min_ang > 3):
                self.fig = self.pc_obj.calib_evolution_Trad(self.diagnostic, ch, used_results, diag_data, std_dev_data, popt_list, pol_ang_list)  # , diag_time_list, diag_data_list
            else:
                self.fig = self.pc_obj.calib_evolution_Trad(self.diagnostic, ch, used_results, diag_data, std_dev_data, popt_list)  # , diag_time_list, diag_data_list
        else:
            self.fig = self.pc_obj.calib_evolution_Trad(self.diagnostic, ch, used_results, diag_data, std_dev_data, popt_list)  # , diag_time_list, diag_data_list
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def OnPlotCalibvsLaunch(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        if(len(self.used) == 0):
            print("Error: No shots marked for plotting!")
            return
        self.pc_obj.reset(True)
        self.fig.clf()
        self.canvas.draw()
        used_results = []
        if(self.diagnostic == "CTC" or self.diagnostic == "IEC" or self.diagnostic == "CTA"):
            beamline = self.ECFM_result_list[0].Config.used_diags_dict[self.diagnostic].beamline
        else:
            print("This plot is only sensible for steerable ECE!")
            return
        pol_ang_list = []
        for result in self.ECFM_result_list:
            if(str(result.Config.shot) + "_ed_" + str(result.edition) in self.used):
                used_results.append(result)
            gy = get_ECRH_viewing_angles(result.Config.shot, beamline, self.ECFM_result_list[0].Config.used_diags_dict[self.diagnostic].base_freq_140)
            pol_ang = []
            for t in result.Config.time:
                pol_ang.append(gy.theta_pol[np.argmin(np.abs(gy.time - t))])
            pol_ang_list.append(np.array(pol_ang))
        ch = self.ch_ch.GetSelection()
        if(ch < 0):
            print("Error!!: No channel selected")
            return
#        diag_time_list = []
#        diag_data_list = []
#        for result in self.ECFM_result_list:
#            diag_time, diag_data = get_diag_data_no_calib(result.used_diags_dict[self.diagnostic], self.Config.shot, preview=True)
#            diag_time_list.append(diag_time)
#            diag_data_list.append(diag_data.T[ch])
        self.fig = self.pc_obj.calib_vs_launch(self.diagnostic, ch, used_results, pol_ang_list)  # , diag_time_list, diag_data_list
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def OnPlotDiagVsTrad(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        if(len(self.used) == 0):
            print("Error: No shots marked for plotting!")
            return
        self.pc_obj.reset(True)
        self.fig.clf()
        self.canvas.draw()
        used_results = []
        for result in self.ECFM_result_list:
            if(str(result.Config.shot) + "_ed_" + str(result.edition) in self.used):
                used_results.append(result)
        ch = self.ch_ch.GetSelection()
        if(ch < 0):
            print("Error!!: No channel selected")
            return
        ECE_diag_exp = self.ECE_diag_exp_tc.GetValue()
        ECE_diag_diag = self.ECE_diag_diag_tc.GetValue()
        ECE_diag_ed = self.ECE_diag_ed_tc.GetValue()
        time_list = []
        calib_diag_trace = []
        Trad_trace = []
        ECE_diag_trace = []
        ECE_diag = Diag("ECE", ECE_diag_exp, ECE_diag_diag, ECE_diag_ed)
        calib_diag = used_results[0].Config.used_diags_dict[self.diagnostic]
        for result in used_results:
            time_list.append(result.Config.time[result.masked_time_points[self.diagnostic]])
            calib_diag_trace.append(np.zeros((len(result.Config.time[result.masked_time_points[self.diagnostic]]), \
                                              len(result.Config.time[result.masked_time_points[self.diagnostic]]))))
            Trad_trace.append(np.zeros(len(result.Config.time[result.masked_time_points[self.diagnostic]])))
            ECE_diag_trace.append(np.zeros((len(result.Config.time[result.masked_time_points[self.diagnostic]]), \
                                            len(result.Config.time[result.masked_time_points[self.diagnostic]]))))
            if(result.Config.extra_output):
                resonances = result.resonance["rhop_warm"]
            else:
                resonances = result.resonance["rhop_cold"]
            if(result.Config.plasma_dict is not None):
                std_dev, data = get_data_calib(diag=calib_diag, shot=result.Config.shot, \
                                               time=result.Config.time[result.masked_time_points[self.diagnostic]], \
                                           eq_exp=result.Config.plasma_dict["eq_exp"], \
                                           eq_diag=result.Config.plasma_dict["eq_diag"], \
                                           eq_ed=result.Config.plasma_dict["eq_ed"], \
                                           calib=result.calib[self.diagnostic], \
                                           std_dev_calib=result.rel_dev[self.diagnostic] * result.calib[self.diagnostic] / 100.0, \
                                           ext_resonances=resonances)
            else:
                std_dev, data = get_data_calib(diag=calib_diag, shot=result.Config.shot, \
                                               time=result.Config.time[result.masked_time_points[self.diagnostic]], \
                                           calib=result.calib[self.diagnostic], \
                                           std_dev_calib=result.rel_dev[self.diagnostic] * result.calib[self.diagnostic] / 100.0, \
                                           ext_resonances=resonances)
            calib_diag_trace[-1][0][:] = data[1].T[ch]
            calib_diag_trace[-1][1][:] = std_dev[0].T[ch]
            Trad_trace[-1][:] = result.Trad[result.masked_time_points[self.diagnostic]].T[ch]
            std_dev, data = get_data_calib(diag=ECE_diag, shot=result.Config.shot, \
                                           time=result.Config.time[result.masked_time_points[self.diagnostic]])
            # print(data[0], data[1])
            for i in range(len(result.Config.time[result.masked_time_points[self.diagnostic]])):
                rhop_calib_diag = resonances[i][ch]
                ECE_diag_trace[-1][0][i] = data[1][i][np.argmin(np.abs(data[0][i] - rhop_calib_diag))]  # eV -> keV # ECE channel closest to warm resonance
                # print("res", rhop_calib_diag, data[0][i][np.argmin(np.abs(data[0][i] - rhop_calib_diag))])
                ECE_diag_trace[-1][1][i] = std_dev[0][i][np.argmin(np.abs(data[0][i] - rhop_calib_diag))]  # eV -> keV
#        diag_time_list = []
#        diag_data_list = []
#        for result in self.ECFM_result_list:
#            diag_time, diag_data = get_diag_data_no_calib(result.Config.used_diags_dict[self.diagnostic], self.Config.shot, preview=True)
#            diag_time_list.append(diag_time)
#            diag_data_list.append(diag_data.T[ch])
        self.fig = self.pc_obj.Trad_vs_diag(self.diagnostic, ch, time_list, calib_diag_trace, Trad_trace, ECE_diag_trace)
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        self.GetEventHandler().ProcessEvent(evt)

    def OnClearAllResults(self, evt):
        self.ECFM_result_list = []
        self.shotlist = []
        self.used_list.Clear()
        self.unused_list.Clear()
        self.used = []
        self.unused = []
        self.ch_ch.Clear()

    def ChangeCursor(self, event):
        if(Phoenix):
            self.canvas.SetCursor(wx.Cursor(wx.CURSOR_CROSS))
        else:
            self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_CROSS))

    def UpdateCoords(self, event):
        if event.inaxes:
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            x, y = event.xdata, event.ydata
            evt.SetStatus('x = {0:1.3e}: y = {1:1.3e}'.format(x, y))
            self.GetEventHandler().ProcessEvent(evt)

class ECFM_GUI_LOS_PlotPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.parent = parent
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.Results = None
        self.FigureControlPanel = FigureBook(self)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.Bind(EVT_THREAD_FINISHED, self.OnThreadFinished)
        self.controlgrid = wx.BoxSizer(wx.HORIZONTAL)
        self.controlgrid2 = wx.BoxSizer(wx.HORIZONTAL)
        self.plot_choice_sizer = wx.BoxSizer(wx.VERTICAL)
        self.plot_choice_label = wx.StaticText(self, wx.ID_ANY, "Plot")
        self.plot_choice = wx.Choice(self, wx.ID_ANY)
        self.plot_choice.Append("Trad")
        self.plot_choice.Append("T")
        self.plot_choice.Append("Trad mode")
        self.plot_choice.Append("T mode")
        self.plot_choice.Append("BPD")
        self.plot_choice.Append("Ray")
        # self.plot_choice.Append("Ray_H_N")
        self.plot_choice.Append("Rz res.")
        self.plot_choice.Append("Rz res. w. rays")
        self.plot_choice.Select(0)
        self.plot_choice_sizer.Add(self.plot_choice_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.plot_choice_sizer.Add(self.plot_choice, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.plot_choice_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.AddPlotButton = wx.Button(self, wx.ID_ANY, 'Add plot')
        self.AddPlotButton.Bind(wx.EVT_BUTTON, self.OnPlot)
        self.ClearButton = wx.Button(self, wx.ID_ANY, 'Clear plots')
        self.Bind(wx.EVT_BUTTON, self.OnClear, self.ClearButton)
        self.MakeTorbeamRaysButton = wx.Button(self, wx.ID_ANY, "Make TORBEAM Rays")
        self.Bind(wx.EVT_BUTTON, self.OnMakeTORBEAMRays, self.MakeTorbeamRaysButton)
        self.time_choice_sizer = wx.BoxSizer(wx.VERTICAL)
        self.time_choice_label = wx.StaticText(self, wx.ID_ANY, "time")
        self.time_choice = wx.Choice(self, wx.ID_ANY)
        self.time_choice_sizer.Add(self.time_choice_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.time_choice_sizer.Add(self.time_choice, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.time_choice_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.ch_choice_sizer = wx.BoxSizer(wx.VERTICAL)
        self.ch_choice_label = wx.StaticText(self, wx.ID_ANY, "Channel")
        self.ch_choice = wx.Choice(self, wx.ID_ANY)
        self.ch_choice.Bind(wx.EVT_CHOICE, self.OnUpdateChtooltip)
        self.ch_choice_sizer.Add(self.ch_choice_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.ch_choice_sizer.Add(self.ch_choice, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.ch_choice_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.mode_cb = simple_label_cb(self, "X-mode", True)
        self.controlgrid.Add(self.mode_cb, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.alt_model_cb = simple_label_cb(self, "show both models", True)
        self.tau_threshhold_tc = simple_label_tc(self, "lower boundary for tau", 0.0, "real")
        self.eq_aspect_ratio_cb = simple_label_cb(self, "Equal aspect ratio", True)
        self.controlgrid.Add(self.alt_model_cb, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid.Add(self.AddPlotButton, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid.Add(self.ClearButton, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid.Add(self.MakeTorbeamRaysButton, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid2.Add(self.tau_threshhold_tc, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid2.Add(self.eq_aspect_ratio_cb, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.sizer.Add(self.controlgrid, 0, \
                                    wx.LEFT | wx.ALL , 10)
        self.sizer.Add(self.controlgrid2, 0, \
                                    wx.LEFT | wx.ALL , 10)
        self.sizer.Add(self.FigureControlPanel, 0, wx.ALL | wx.LEFT, 10)
        self.FigureControlPanel.Show(True)
        self.cur_selected_index = 0

    def OnUpdate(self, evt):
        self.Config = evt.Config
        self.Results = evt.data
        if(len(self.Config.time) > 0):
            self.time_choice.Clear()
            self.time_choice.AppendItems(self.Config.time.astype("|S7"))
            self.time_choice.Select(0)
            self.ch_choice.Clear()
            self.ch_choice.AppendItems(np.array(range(1, len(self.Results.Trad.T) + 1)).astype("|S4"))
            self.ch_choice.Select(0)

    def OnUpdateChtooltip(self, evt):
        if(len(self.Config.time) > 0):
            time = float(self.time_choice.GetStringSelection())
            itime = np.argmin(np.abs(self.Results.Config.time - time))
            ch = int(self.ch_choice.GetStringSelection()) - 1
            res = self.Results.resonance["rhop_cold"][itime][ch]
            if(Phoenix):
                self.ch_choice.SetToolTip(r"rhopol = {0:1.3f}".format(res))
            else:
                self.ch_choice.SetToolTipString(r"rhopol = {0:1.3f}".format(res))

    def OnPlot(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - GUI might be unresponsive for minutes - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        plot_type = self.plot_choice.GetStringSelection()
        time = float(self.time_choice.GetStringSelection())
        ch = int(self.ch_choice.GetStringSelection()) - 1  # index - not channel number
        mode = self.mode_cb.GetValue()
        alt_model = self.alt_model_cb.GetValue()
        tau_threshhold = self.tau_threshhold_tc.GetValue()
        eq_aspect_ratio = self.eq_aspect_ratio_cb.GetValue()
        self.FigureControlPanel.AddPlot(plot_type, self.Config, self.Results, time, ch, mode, alt_model, tau_threshhold, eq_aspect_ratio)
        self.SetClientSize(self.GetEffectiveMinSize())

    def OnMakeTORBEAMRays(self, evt):
        try:
            if(len(self.Config.time) == 0):
                print("No .mat loaded")
                return
        except AttributeError:
            print("No .mat loaded")
            return
        time = float(self.time_choice.GetStringSelection())
        if(self.mode_cb.GetValue()):
            mode = -1
            self.cur_mode_str = "X"
        else:
            mode = +1
            self.cur_mode_str = "O"
        self.cur_selected_index = np.argmin(np.abs(self.Config.time - time))
        print("Calculating rays with TORBEAM hold on")
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Calculating rays with TORBEAM hold on')
        self.GetEventHandler().ProcessEvent(evt)
        wt = WorkerThread(make_all_TORBEAM_rays_thread, [self.Config.working_dir, \
                          self.Config.shot, time, self.Config.plasma_dict["eq_exp"], \
                          self.Config.plasma_dict["eq_diag"], self.Config.plasma_dict["eq_ed"], \
                          self.Results.ray_launch, self.cur_selected_index, mode, self.Config.plasma_dict, \
                          self, self.Config.bt_vac_correction, self.Config.N_ray])

    def OnThreadFinished(self, evt):
        print("Updating ray information")
        ray_path = os.path.join(self.Config.working_dir, "ecfm_data", "ray")
        if("x" + self.cur_mode_str + "tb" in self.Results.ray.keys()):
            for channel in range(len(self.Results.ray["x" + self.cur_mode_str][self.cur_selected_index])):
                TBRay_file = np.loadtxt(os.path.join(ray_path, "ray_ch_R{0:04n}tb.dat".format(channel + 1)).replace(",", ""))
                TBXRay_file = np.loadtxt(os.path.join(ray_path, "ray_ch_x{0:04n}tb.dat".format(channel + 1)).replace(",", ""))
                self.Results.ray["x" + self.cur_mode_str + "tb"][self.cur_selected_index].append(TBXRay_file.T[0] / 100.0)
                self.Results.ray["y" + self.cur_mode_str + "tb"][self.cur_selected_index].append(TBXRay_file.T[1] / 100.0)
                self.Results.ray["R" + self.cur_mode_str + "tb"][self.cur_selected_index].append(TBRay_file.T[0] / 100.0)
                self.Results.ray["z" + self.cur_mode_str + "tb"][self.cur_selected_index].append(TBRay_file.T[1] / 100.0)
                self.Results.ray["x" + self.cur_mode_str + "tbp1"][self.cur_selected_index].append(TBXRay_file.T[2] / 100.0)
                self.Results.ray["y" + self.cur_mode_str + "tbp1"][self.cur_selected_index].append(TBXRay_file.T[3] / 100.0)
                self.Results.ray["R" + self.cur_mode_str + "tbp1"][self.cur_selected_index].append(TBRay_file.T[2] / 100.0)
                self.Results.ray["z" + self.cur_mode_str + "tbp1"][self.cur_selected_index].append(TBRay_file.T[3] / 100.0)
                self.Results.ray["x" + self.cur_mode_str + "tbp2"][self.cur_selected_index].append(TBXRay_file.T[4] / 100.0)
                self.Results.ray["y" + self.cur_mode_str + "tbp2"][self.cur_selected_index].append(TBXRay_file.T[5] / 100.0)
                self.Results.ray["R" + self.cur_mode_str + "tbp2"][self.cur_selected_index].append(TBRay_file.T[4] / 100.0)
                self.Results.ray["z" + self.cur_mode_str + "tbp2"][self.cur_selected_index].append(TBRay_file.T[5] / 100.0)
        else:
            self.Results.ray["x" + self.cur_mode_str + "tb"] = []
            self.Results.ray["y" + self.cur_mode_str + "tb"] = []
            self.Results.ray["R" + self.cur_mode_str + "tb"] = []
            self.Results.ray["z" + self.cur_mode_str + "tb"] = []
            self.Results.ray["x" + self.cur_mode_str + "tbp1"] = []
            self.Results.ray["y" + self.cur_mode_str + "tbp1"] = []
            self.Results.ray["R" + self.cur_mode_str + "tbp1"] = []
            self.Results.ray["z" + self.cur_mode_str + "tbp1"] = []
            self.Results.ray["x" + self.cur_mode_str + "tbp2"] = []
            self.Results.ray["y" + self.cur_mode_str + "tbp2"] = []
            self.Results.ray["R" + self.cur_mode_str + "tbp2"] = []
            self.Results.ray["z" + self.cur_mode_str + "tbp2"] = []
            for i in range(len(self.Config.time)):
                self.Results.ray["x" + self.cur_mode_str + "tb"].append([])
                self.Results.ray["y" + self.cur_mode_str + "tb"].append([])
                self.Results.ray["R" + self.cur_mode_str + "tb"].append([])
                self.Results.ray["z" + self.cur_mode_str + "tb"].append([])
                self.Results.ray["x" + self.cur_mode_str + "tbp1"].append([])
                self.Results.ray["y" + self.cur_mode_str + "tbp1"].append([])
                self.Results.ray["R" + self.cur_mode_str + "tbp1"].append([])
                self.Results.ray["z" + self.cur_mode_str + "tbp1"].append([])
                self.Results.ray["x" + self.cur_mode_str + "tbp2"].append([])
                self.Results.ray["y" + self.cur_mode_str + "tbp2"].append([])
                self.Results.ray["R" + self.cur_mode_str + "tbp2"].append([])
                self.Results.ray["z" + self.cur_mode_str + "tbp2"].append([])
                if(i == self.cur_selected_index):
                    for channel in range(len(self.Results.ray["x" + self.cur_mode_str][i])):
                        TBRay_file = np.loadtxt(os.path.join(ray_path, "ray_ch_R{0:04n}tb.dat".format(channel + 1)).replace(",", ""))
                        TBXRay_file = np.loadtxt(os.path.join(ray_path, "ray_ch_x{0:04n}tb.dat".format(channel + 1)).replace(",", ""))
                        self.Results.ray["x" + self.cur_mode_str + "tb"][i].append(TBXRay_file.T[0] / 100.0)
                        self.Results.ray["y" + self.cur_mode_str + "tb"][i].append(TBXRay_file.T[1] / 100.0)
                        self.Results.ray["R" + self.cur_mode_str + "tb"][i].append(TBRay_file.T[0] / 100.0)
                        self.Results.ray["z" + self.cur_mode_str + "tb"][i].append(TBRay_file.T[1] / 100.0)
                        self.Results.ray["x" + self.cur_mode_str + "tbp1"][i].append(TBXRay_file.T[2] / 100.0)
                        self.Results.ray["y" + self.cur_mode_str + "tbp1"][i].append(TBXRay_file.T[3] / 100.0)
                        self.Results.ray["R" + self.cur_mode_str + "tbp1"][i].append(TBRay_file.T[2] / 100.0)
                        self.Results.ray["z" + self.cur_mode_str + "tbp1"][i].append(TBRay_file.T[3] / 100.0)
                        self.Results.ray["x" + self.cur_mode_str + "tbp2"][i].append(TBXRay_file.T[4] / 100.0)
                        self.Results.ray["y" + self.cur_mode_str + "tbp2"][i].append(TBXRay_file.T[5] / 100.0)
                        self.Results.ray["R" + self.cur_mode_str + "tbp2"][i].append(TBRay_file.T[4] / 100.0)
                        self.Results.ray["z" + self.cur_mode_str + "tbp2"][i].append(TBRay_file.T[5] / 100.0)

    def OnClear(self, evt):
        self.FigureControlPanel.ClearFigureBook()

class FigureBook(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, wx.ID_ANY)
        self.FigureList = []

    def AddPlot(self, plot_type, Config, Results, time, ch, mode, alt_model, tau_threshhold, eq_aspect_ratio):
        self.FigureList.append(PlotContainer(self))
        if(self.FigureList[-1].Plot(plot_type, Config, Results, time, ch, mode, alt_model, tau_threshhold, eq_aspect_ratio)):
            if(plot_type == "Trad" or plot_type == "Rz_Res"):
                self.AddPage(self.FigureList[-1], plot_type + " t = {0:2.3f} s".format(time))
            else:
                self.AddPage(self.FigureList[-1], plot_type + " t = {0:2.3f} s".format(time) + " Channel " + str(ch + 1))
        else:
            del(self.FigureList[-1])
            return
        if(not self.IsShown()):
            self.Show(True)
        self.SetClientSize(self.GetEffectiveMinSize())
        return 0

    def ClearFigureBook(self):
        while self.GetPageCount() > 0:
            self.RemovePage(0)


class PlotContainer(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.fig_sizer = wx.BoxSizer(wx.VERTICAL)
        self.fig = plt.figure(figsize=(12.0, 8.5), tight_layout=False)
        self.fig.clf()
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.canvas.mpl_connect('motion_notify_event', self.UpdateCoords)
        self.canvas.draw()
        self.plot_toolbar = NavigationToolbar2Wx(self.canvas)
        fw, th = self.plot_toolbar.GetSize().Get()
        self.plot_toolbar.SetSize(wx.Size(fw, th))
        self.plot_toolbar.Realize()
        self.fig_sizer.Add(self.plot_toolbar, 0, wx.ALL | \
                wx.LEFT , 5)
        self.fig_sizer.Add(self.canvas, 0, wx.ALL | \
                wx.EXPAND , 5)
        # self.fig_H_sizer = wx.BoxSizer(wx.VERTICAL)
        # self.fig_H = plt.figure(figsize=(12.0, 8.5), tight_layout=False)
        # self.fig_H.clf()
        # self.canvas_H = FigureCanvas(self, -1, self.fig_H)
        # self.canvas_H.mpl_connect('motion_notify_event', self.UpdateCoords)
        # self.canvas_H.draw()
        # self.plot_toolbar_H = NavigationToolbar2Wx(self.canvas_H)
        # fw, th = self.plot_toolbar_H.GetSize().Get()
        # self.plot_toolbar_H.SetSize(wx.Size(fw, th))
        # self.plot_toolbar_H.Realize()
        # self.fig_H_sizer.Add(self.plot_toolbar_H, 0, wx.ALL | \
        #        wx.LEFT , 5)
        # self.fig_H_sizer.Add(self.canvas_H, 0, wx.ALL | \
        #        wx.EXPAND , 5)
        self.sizer.Add(self.fig_sizer, 0, wx.ALL | wx.EXPAND , 5)
        # self.sizer.Add(self.fig_H_sizer, 0, wx.ALL | wx.EXPAND , 5)
        self.pc_obj = plotting_core(self.fig, title=False)
        self.SetClientSize(self.GetEffectiveMinSize())

    def Plot(self, plot_type, Config, Results, time, ch, mode, alt_model, tau_threshhold, eq_aspect_ratio):
        self.pc_obj.reset(True)
        if(len(Config.time) == 0):
            print("No time points! - Did you select new IDA timepoints?")
            return
        time_index = np.argmin(np.abs(Config.time - time))
        straight = False
        if(mode):
            mode_str = 'X'
        else:
            mode_str = 'O'
        if(plot_type == "Ray"):
            if(not Config.extra_output):
                print("The rays were not output by ECRad!")
                print(r"Rerun ECRad with \"extra output\" set to True")
                return
            if(len(Results.ray["s" + mode_str]) == 0):
                print(mode_str + "-mode was not included in the calculation")
                return
            elif(len(Results.ray["s" + mode_str][time_index][ch]) == 0):
                print(mode_str + "-mode was not included in the calculation")
                return
            try:
                try:
                    rays = []
                    if(np.iterable(Results.ray["s" + mode_str][time_index][ch][0])):
                        ir = 0
                        cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                              Results.ray["x" + mode_str][time_index][ch][ir], \
                              Results.ray["y" + mode_str][time_index][ch][ir], \
                              Results.ray["z" + mode_str][time_index][ch][ir], \
                              Results.ray["H" + mode_str][time_index][ch][ir], \
                              Results.ray["N" + mode_str][time_index][ch][ir], \
                              Results.ray["Nc" + mode_str][time_index][ch][ir], \
                              x_tb=Results.ray["x" + mode_str + "tb"][time_index][ch], \
                              y_tb=Results.ray["y" + mode_str + "tb"][time_index][ch], \
                              z_tb=Results.ray["z" + mode_str + "tb"][time_index][ch], \
                              x_tbp1=Results.ray["x" + mode_str + "tbp1"][time_index][ch], \
                              y_tbp1=Results.ray["y" + mode_str + "tbp1"][time_index][ch], \
                              z_tbp1=Results.ray["z" + mode_str + "tbp1"][time_index][ch], \
                              x_tbp2=Results.ray["x" + mode_str + "tbp1"][time_index][ch], \
                              y_tbp2=Results.ray["y" + mode_str + "tbp2"][time_index][ch], \
                              z_tbp2=Results.ray["z" + mode_str + "tbp2"][time_index][ch])
                        rays.append(cur_ray)
                        for ir in range(1, len(Results.ray["s" + mode_str][time_index][ch])):
                            cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                              Results.ray["x" + mode_str][time_index][ch][ir], \
                              Results.ray["y" + mode_str][time_index][ch][ir], \
                              Results.ray["z" + mode_str][time_index][ch][ir], \
                              Results.ray["H" + mode_str][time_index][ch][ir], \
                              Results.ray["N" + mode_str][time_index][ch][ir], \
                              Results.ray["Nc" + mode_str][time_index][ch][ir])
                            rays.append(cur_ray)
                    else:
                        cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch], \
                              Results.ray["x" + mode_str][time_index][ch], \
                              Results.ray["y" + mode_str][time_index][ch], \
                              Results.ray["z" + mode_str][time_index][ch], \
                              Results.ray["H" + mode_str][time_index][ch], \
                              Results.ray["N" + mode_str][time_index][ch], \
                              Results.ray["Nc" + mode_str][time_index][ch], \
                              x_tb=Results.ray["x" + mode_str + "tb"][time_index][ch], \
                              y_tb=Results.ray["y" + mode_str + "tb"][time_index][ch], \
                              z_tb=Results.ray["z" + mode_str + "tb"][time_index][ch])
                        rays.append(cur_ray)
                except KeyError:
                    print("No TORBEAM rays found")
                    print("Availabe keys", Results.ray.keys())
                    rays = []
                    straight = True
                    if(alt_model):
                        straight_rays = []
                    if(np.iterable(Results.ray["s" + mode_str][time_index][ch][0])):
                        ir = 0
                        cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                              Results.ray["x" + mode_str][time_index][ch][ir], \
                              Results.ray["y" + mode_str][time_index][ch][ir], \
                              Results.ray["z" + mode_str][time_index][ch][ir], \
                              Results.ray["H" + mode_str][time_index][ch][ir], \
                              Results.ray["N" + mode_str][time_index][ch][ir], \
                              Results.ray["Nc" + mode_str][time_index][ch][ir])
                        rays.append(cur_ray)
                        for ir in range(1, len(Results.ray["s" + mode_str][time_index][ch])):
                            if(alt_model):
                                x0 = Results.ray["x" + mode_str][time_index][ch][ir][::-1][0]
                                x1 = Results.ray["x" + mode_str][time_index][ch][ir][::-1][40]
                                y0 = Results.ray["y" + mode_str][time_index][ch][ir][::-1][0]
                                y1 = Results.ray["y" + mode_str][time_index][ch][ir][::-1][40]
                                z0 = Results.ray["z" + mode_str][time_index][ch][ir][::-1][0]
                                z1 = Results.ray["z" + mode_str][time_index][ch][ir][::-1][40]
                                delta_s = Results.ray["s" + mode_str][time_index][ch][0][np.argmax(np.sqrt((Results.ray["x" + mode_str][time_index][ch][0] - \
                                                                                                            Results.ray["x" + mode_str][time_index][ch][0][-1]) ** 2 + \
                                                                                                           (Results.ray["y" + mode_str][time_index][ch][0] - \
                                                                                                            Results.ray["y" + mode_str][time_index][ch][0][-1]) ** 2))]
                                s = np.linspace(0.0, delta_s, 100)
                                x = x0 + s * (x1 - x0)
                                y = y0 + s * (y1 - y0)
                                z = z0 + s * (z1 - z0)
                                cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                                  Results.ray["x" + mode_str][time_index][ch][ir], \
                                  Results.ray["y" + mode_str][time_index][ch][ir], \
                                  Results.ray["z" + mode_str][time_index][ch][ir], \
                                  Results.ray["H" + mode_str][time_index][ch][ir], \
                                  Results.ray["N" + mode_str][time_index][ch][ir], \
                                  Results.ray["Nc" + mode_str][time_index][ch][ir], \
                                  x_tb=x, y_tb=y, z_tb=z)
                            else:
                                cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch][ir], \
                                  Results.ray["x" + mode_str][time_index][ch][ir], \
                                  Results.ray["y" + mode_str][time_index][ch][ir], \
                                  Results.ray["z" + mode_str][time_index][ch][ir], \
                                  Results.ray["H" + mode_str][time_index][ch][ir], \
                                  Results.ray["N" + mode_str][time_index][ch][ir], \
                                  Results.ray["Nc" + mode_str][time_index][ch][ir])
                            rays.append(cur_ray)
                    else:
                        if(alt_model):
                            x0 = Results.ray["x" + mode_str][time_index][ch][::-1][0]
                            x1 = Results.ray["x" + mode_str][time_index][ch][::-1][40]
                            y0 = Results.ray["y" + mode_str][time_index][ch][::-1][0]
                            y1 = Results.ray["y" + mode_str][time_index][ch][::-1][40]
                            z0 = Results.ray["z" + mode_str][time_index][ch][::-1][0]
                            z1 = Results.ray["z" + mode_str][time_index][ch][::-1][40]
                            delta_s = np.max(Results.ray["s" + mode_str][time_index][ch])
                            s = np.linspace(0.0, delta_s, 100)
                            ds = Results.ray["s" + mode_str][time_index][ch][::-1][0] - Results.ray["s" + mode_str][time_index][ch][::-1][40]
                            x = x0 + s / ds * (x1 - x0)
                            y = y0 + s / ds * (y1 - y0)
                            z = z0 + s / ds * (z1 - z0)
                            cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch], \
                              Results.ray["x" + mode_str][time_index][ch], \
                              Results.ray["y" + mode_str][time_index][ch], \
                              Results.ray["z" + mode_str][time_index][ch], \
                              Results.ray["H" + mode_str][time_index][ch], \
                              Results.ray["N" + mode_str][time_index][ch], \
                              Results.ray["Nc" + mode_str][time_index][ch], \
                              x_tb=x, y_tb=y, z_tb=z)
                        else:
                            cur_ray = Ray(Results.ray["s" + mode_str][time_index][ch], \
                            Results.ray["x" + mode_str][time_index][ch], \
                            Results.ray["y" + mode_str][time_index][ch], \
                            Results.ray["z" + mode_str][time_index][ch], \
                            Results.ray["H" + mode_str][time_index][ch], \
                            Results.ray["N" + mode_str][time_index][ch], \
                            Results.ray["Nc" + mode_str][time_index][ch])
                            rays.append(cur_ray)
                        rays.append(cur_ray)
            except KeyError:
                print("Error: No ray information in currently loaded data set")
                return False
            s_cold = Results.resonance["R_cold"][time_index][ch]
            R_cold = Results.resonance["R_cold"][time_index][ch]
            z_cold = Results.resonance["z_cold"][time_index][ch]
            if(Config.Ext_plasma != False):
                EQ_obj = EQData(Config.shot)
                EQ_obj.insert_slices_from_ext(Config.time, Config.plasma_dict["eq_data"], transpose=True)
                # the matrices in the slices are Fortran ordered - hence transposition necessary
                self.fig = self.pc_obj.plot_ray(Config.shot, time, rays, index=time_index, \
                                            EQ_obj=EQ_obj, H=False, R_cold=R_cold, \
                                            z_cold=z_cold, s_cold=s_cold, straight=straight, eq_aspect_ratio=eq_aspect_ratio)
            else:
                self.fig = self.pc_obj.plot_ray(Config.shot, time, rays, index=time_index, \
                                            H=False, R_cold=R_cold, \
                                            z_cold=z_cold, s_cold=s_cold, straight=straight, eq_aspect_ratio=eq_aspect_ratio)
            self.canvas.draw()
            evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)
        if(plot_type == "Ray_H_N"):
            print("Coming soon - sorry!")
            return False
        elif(plot_type == "Trad"):
            rhop = Results.resonance["rhop_cold"][time_index][Results.tau[time_index] >= tau_threshhold]
            if(len(rhop) == 0):
                print("No channels have an optical depth below the currently selected threshold!")
                return False
            Trad = Results.Trad[time_index][Results.tau[time_index] >= tau_threshhold]
            if(alt_model):
                if(Results.Config.extra_output):
                    Trad_comp = Results.Trad_comp[time_index][Results.tau[time_index] >= tau_threshhold]
                else:
                    Trad_comp = []
                    print("Secondary model was deactivated during the run.")
                    print("To enable it, activate extra outout und rerun ECFM!")
            else:
                Trad_comp = []
            rhop_IDA = Config.plasma_dict["rhop"][time_index]
            Te_IDA = Config.plasma_dict["Te"][time_index] / 1.e3
            if(Config.Ext_plasma == False):
                try:
                    rhop_ECE = Config.plasma_dict["ECE_rhop"][time_index]
                    if(Config.plasma_dict["ECE_dat"][time_index].ndim == 2):
                        ECE_dat = np.mean(Config.plasma_dict["ECE_dat"][time_index] / 1.e3, axis=0)
                        ECE_err = np.mean(Config.plasma_dict["ECE_unc"][time_index] / 1.e3, axis=0)
                    else:
                        print(Config.plasma_dict["ECE_dat"])
                        ECE_dat = Config.plasma_dict["ECE_dat"][time_index] / 1.e3
                        ECE_err = Config.plasma_dict["ECE_unc"][time_index] / 1.e3
                    ECE_mod = Config.plasma_dict["ECE_mod"][time_index] / 1.e3
                    self.fig = self.pc_obj.plot_Trad(time, rhop, Trad, Trad_comp, \
                                                     rhop_IDA, Te_IDA, \
                                                     rhop_ECE, ECE_dat, ECE_err, ECE_mod, Config.dstf, alt_model)
                except IndexError:
                    print("Something wrong with the IDA data - plotting only fwd. model data")
                    self.fig = self.pc_obj.plot_Trad(time, rhop, Trad, Trad_comp, \
                                                     rhop_IDA, Te_IDA, \
                                                    [], [], [], [], Config.dstf, alt_model)
            else:
                self.fig = self.pc_obj.plot_Trad(time, rhop, Trad, Trad_comp, \
                                                 rhop_IDA, Te_IDA, \
                                                 [], [], [], [], Config.dstf, alt_model)
        elif(plot_type == "T"):
            rhop = Results.resonance["rhop_cold"][time_index][Results.tau[time_index] >= tau_threshhold]
            if(len(rhop) == 0):
                print("No channels have an optical depth below the currently selected threshold!")
                return False
            tau = Results.tau[time_index][Results.tau[time_index] >= tau_threshhold]
            if(Results.Config.extra_output):
                tau_comp = Results.tau_comp[time_index][Results.tau[time_index] >= tau_threshhold]
            else:
                tau_comp = None
            rhop_IDA = Config.plasma_dict["rhop"][time_index]
            Te_IDA = Config.plasma_dict["Te"][time_index] / 1.e3
            self.fig = self.pc_obj.plot_tau(time, rhop, \
                                            tau, tau_comp, rhop_IDA, Te_IDA, \
                                            Config.dstf, alt_model)
            self.canvas.draw()
            evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)
        elif(plot_type == "Trad mode"):
            if(Config.considered_modes != 3):
                print("This plot is only sensitble if both X and O mode are considered")
                return
            if(not Config.extra_output):
                print("Extra ouput must be set to true for this information to be available")
                print("Please rerun ECRad with 'extra output' set to True")
                return
            if(len(Results.XTrad) == 0):
                print("No information on the individual X and O mode fractions availabe")
                print("This information was not stored in the result files previously, please rerun ECRad")
                return
            if(mode):
                # X-mode
                rhop = Results.resonance["rhop_cold"][time_index][Results.Xtau[time_index] >= tau_threshhold]
                Trad = Results.XTrad[time_index][Results.Xtau[time_index] >= tau_threshhold]
                X_mode_frac = Results.X_mode_frac[time_index][Results.Xtau[time_index] >= tau_threshhold]
                Trad_comp = Results.XTrad_comp[time_index][Results.Xtau[time_index] >= tau_threshhold]
                X_mode_frac_comp = Results.X_mode_frac_comp[time_index][Results.Xtau[time_index] >= tau_threshhold]

            else:
                # O-mode
                rhop = Results.resonance["rhop_cold"][time_index][Results.Otau[time_index] >= tau_threshhold]
                Trad = Results.OTrad[time_index][Results.Otau[time_index] >= tau_threshhold]
                Trad_comp = Results.OTrad_comp[time_index][Results.Otau[time_index] >= tau_threshhold]
                X_mode_frac = Results.X_mode_frac[time_index][Results.Otau[time_index] >= tau_threshhold]
                X_mode_frac_comp = Results.X_mode_frac_comp[time_index][Results.Otau[time_index] >= tau_threshhold]
            rhop_IDA = Config.plasma_dict["rhop"][time_index]
            Te_IDA = Config.plasma_dict["Te"][time_index] / 1.e3
            self.fig = self.pc_obj.plot_Trad(time, rhop, Trad, Trad_comp, \
                                              rhop_IDA, Te_IDA, \
                                              [], [], [], [], Config.dstf, alt_model, \
                                               X_mode_fraction=X_mode_frac, \
                                               X_mode_fraction_comp=X_mode_frac_comp)
        elif(plot_type == "T mode"):
            if(Config.considered_modes != 3):
                print("This plot is only sensitble if both X and O mode are considered")
                return
            if(not Config.extra_output):
                print("Extra ouput must be set to true for this information to be available")
                print("Please rerun ECRad with 'extra output' set to True")
                return
            if(len(Results.XTrad) == 0):
                print("No information on the individual X and O mode fractions availabe")
                print("This information was not stored in the result files previously, please rerun ECRad")
                return
            if(mode):
                # X-mode
                rhop = Results.resonance["rhop_cold"][time_index][Results.Xtau[time_index] >= tau_threshhold]
                tau = Results.Xtau[time_index][Results.Xtau[time_index] >= tau_threshhold]
                tau_comp = Results.Xtau_comp[time_index][Results.Xtau[time_index] >= tau_threshhold]
            else:
                # O-mode
                rhop = Results.resonance["rhop_cold"][time_index][Results.Otau[time_index] >= tau_threshhold]
                tau = Results.Otau[time_index][Results.Otau[time_index] >= tau_threshhold]
                tau_comp = Results.Otau_comp[time_index][Results.Otau[time_index] >= tau_threshhold]
            rhop_IDA = Config.plasma_dict["rhop"][time_index]
            Te_IDA = Config.plasma_dict["Te"][time_index] / 1.e3
            self.fig = self.pc_obj.plot_tau(time, rhop, \
                                            tau, tau_comp, rhop_IDA, Te_IDA, \
                                            Config.dstf, alt_model)
        elif(plot_type == "BPD"):
            if(not Config.extra_output):
                print("Birthplace distribution was not computed")
                print("Rerun ECRad with 'extra output' set to True")
                return
            # R = Results.los["R" + mode_str][time_index][ch]
            rhop_IDA = Config.plasma_dict["rhop"][time_index]
            Te_IDA = Config.plasma_dict["Te"][time_index] / 1.e3
            if(mode):
                if(len(Results.BPD["rhopX"]) == 0):
                    print("No data availabe for X-mode")
                rhop = Results.BPD["rhopX"][time_index][ch]
                D = Results.BPD["BPDX"][time_index][ch]
                D_comp = Results.BPD["BPD_secondX"][time_index][ch]
            else:
                if(len(Results.BPD["rhopO"]) == 0):
                    print("No data availabe for O-mode")
                    return False
                rhop = Results.BPD["rhopO"][time_index][ch]
                D = Results.BPD["BPDO"][time_index][ch]
                D_comp = Results.BPD["BPD_secondO"][time_index][ch]
            rhop_cold = Results.resonance["rhop_cold"][time_index][ch]
            if(Config.Ext_plasma == True):
                EQ_obj = EQData(Config.shot)
                EQ_obj.insert_slices_from_ext(Config.time, Config.plasma_dict["eq_data"], transpose=True)
                # the matrices in the slices are Fortran ordered - hence transposition necessary
            else:
                EQ_obj = EQData(Config.shot, EQ_exp=Config.EQ_exp, EQ_diag=Config.EQ_diag, \
                                EQ_ed=Config.EQ_ed)
            R_axis, z_axis = EQ_obj.get_axis(Config.time[time_index])
            if(Results.resonance["R_cold"][time_index][ch] < R_axis):
                rhop_cold *= -1.0
            self.fig = self.pc_obj.plot_BPD(time, rhop, D, D_comp, rhop_IDA, Te_IDA, Config.dstf, rhop_cold)
            self.canvas.draw()
            evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)
        elif(plot_type == "Rz res."):
            R_cold = Results.resonance["R_cold"][time_index][Results.tau[time_index] >= tau_threshhold]
            z_cold = Results.resonance["z_cold"][time_index][Results.tau[time_index] >= tau_threshhold]
            if(Config.extra_output):
                R_warm = Results.resonance["R_warm"][time_index][Results.tau[time_index] >= tau_threshhold]
                z_warm = Results.resonance["z_warm"][time_index][Results.tau[time_index] >= tau_threshhold]
            else:
                print("Warm resonances were not computed")
                print("Rerun ECRad with 'extra output' set to True")
                R_warm = []
                z_warm = []
            if(len(R_cold) == 0):
                print("No channels have an optical depth below the currently selected threshold!")
                return False
#            if(alt_model):
#                if(mode):
#                    R_warm_comp = np.zeros(np.size(Results.birthplace_X_comp, axis=1))
#                    z_warm_comp = np.zeros(np.size(Results.birthplace_X_comp, axis=1))
#                    for ich in range(len(R_warm_comp)):
#                        R_warm_comp[ich] = Results.los["RX"][time_index][ich][np.argmax(Results.birthplace_X_comp[time_index][ich])]
#                        z_warm_comp[ich] = Results.los["zX"][time_index][ich][np.argmax(Results.birthplace_X_comp[time_index][ich])]
#                else:
#                    R_warm_comp = np.zeros(np.size(Results.birthplace_O_comp, axis=1))
#                    z_warm_comp = np.zeros(np.size(Results.birthplace_O_comp, axis=1))
#                    for ich in range(len(R_warm_comp)):
#                        R_warm_comp[ich] = Results.los["RO"][time_index][ich][np.argmax(Results.birthplace_O_comp[time_index][ich])]
#                        z_warm_comp[ich] = Results.los["zO"][time_index][ich][np.argmax(Results.birthplace_O_comp[time_index][ich])]
#                R_warm_comp = R_warm_comp[Results.tau[time_index] > tau_threshhold]
#                z_warm_comp = z_warm_comp[Results.tau[time_index] > tau_threshhold]
#                self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
#                                                   plasma=Config.plasma_dict, R_warm_comp=R_warm_comp, z_warm_comp=z_warm_comp)
#            else:
            if(Config.Ext_plasma == True):
                EQ_obj = EQData(Config.shot)
                EQ_obj.insert_slices_from_ext(Config.time, Config.plasma_dict["eq_data"], transpose=True)
                # the matrices in the slices are Fortran ordered - hence transposition necessary
                self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
                                                   EQ_obj=EQ_obj, eq_aspect_ratio=eq_aspect_ratio)
            else:
                self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
                                                   EQ_exp=Config.EQ_exp, EQ_diag=Config.EQ_diag, \
                                                   EQ_ed=Config.EQ_ed, eq_aspect_ratio=eq_aspect_ratio)
            self.canvas.draw()
            evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)
        elif(plot_type == "Rz res. w. rays"):
            if(not Config.extra_output):
                print("The rays were not output by ECRad only showing cold resonances")
                print("Rerun ECRad with 'extra output' set to True")
            R_cold = Results.resonance["R_cold"][time_index][Results.tau[time_index] > tau_threshhold]
            z_cold = Results.resonance["z_cold"][time_index][Results.tau[time_index] > tau_threshhold]
            if(Config.extra_output):
                R_warm = Results.resonance["R_warm"][time_index][Results.tau[time_index] >= tau_threshhold]
                z_warm = Results.resonance["z_warm"][time_index][Results.tau[time_index] >= tau_threshhold]
            else:
                print("Warm resonances were not computed")
                print("Rerun ECRad with 'extra output' set to True")
                R_warm = []
                z_warm = []
            rays = []
            tb_rays = []
            if(len(Results.ray["s" + mode_str]) == 0):
                print(mode_str + "-mode was not included in the calculation")
                return
            elif(len(Results.ray["s" + mode_str][time_index][ch]) == 0):
                print(mode_str + "-mode was not included in the calculation")
                return
            try:
                if(not np.isscalar(Results.ray["x" + mode_str][time_index][0][0])):
                    for ich in range(len(Results.ray["x" + mode_str][time_index])):
                        i_min = 0
                        if(mode_str == "X"):
                            points_w_emission = np.where(Results.ray["BPDX"][time_index][ich][0] > 1.e-20)  # Central ray
                            if(len(points_w_emission) > 0):
                                i_min = np.min(points_w_emission)
                        else:
                            points_w_emission = np.where(Results.ray["BPDO"][time_index][ich][0] > 1.e-20)  # Central ra
                            if(len(points_w_emission) > 0):
                                i_min = np.min(points_w_emission)
                        rays.append([np.sqrt(Results.ray["x" + mode_str][time_index][ich][0][i_min:] ** 2 + Results.ray["y" + mode_str][time_index][ich][0][i_min:] ** 2), Results.ray["z" + mode_str][time_index][ich][0][i_min:]])
                    rays = np.array(rays)[Results.tau[time_index] > tau_threshhold]
                else:
                    for ich in range(len(Results.ray["x" + mode_str][time_index])):
                        i_min = 0
                        if(mode_str == "X"):
                            points_w_emission = np.where(Results.ray["BPDX"][time_index][ich] > 1.e-20)[0]  # Central ray
                            if(len(points_w_emission) > 0):
                                i_min = np.min(points_w_emission)
                        else:
                            points_w_emission = np.where(Results.ray["BPDO"][time_index][ich] > 1.e-20)[0]  # Central ray
                            if(len(points_w_emission) > 0):
                                i_min = np.min(points_w_emission)
                        rays.append([np.sqrt(Results.ray["x" + mode_str][time_index][ich][i_min:] ** 2 + Results.ray["y" + mode_str][time_index][ich][i_min:] ** 2), Results.ray["z" + mode_str][time_index][ich][i_min:]])
                    rays = np.array(rays)[Results.tau[time_index] > tau_threshhold]
                try:
                    for ich in range(len(Results.ray["x" + mode_str + "tb"][time_index])):
                        tb_rays.append([Results.ray["R" + mode_str + "tb"][time_index][ich], \
                                        Results.ray["z" + mode_str + "tb"][time_index][ich]])
                    tb_rays = np.array(tb_rays)[Results.tau[time_index] > tau_threshhold]
                    if(Config.Ext_plasma == False):
                        EQ_obj = EQData(Config.shot)
                        EQ_obj.insert_slices_from_ext(Config.time, Config.plasma_dict["eq_data"])
                        self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
                                                           EQ_obj=EQ_obj, Rays=rays, tb_Rays=tb_rays)
                    else:
                        self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
                                                           Rays=rays, tb_Rays=tb_rays)
                except KeyError:
                    print("No TORBEAM rays available")
                    if(alt_model):
                        if(len(Results.ray["x" + mode_str][time_index]) == 0):
                            print("For " + mode_str + " mode there is no data")
                            return False
                        straight_rays = []
                        for ich in range(len(Results.ray["x" + mode_str][time_index])):
                            if(not np.isscalar(Results.ray["x" + mode_str][time_index][0][0])):
                                R0 = np.sqrt(Results.ray["x" + mode_str][time_index][ich][0][::-1][0] ** 2 + Results.ray["y" + mode_str][time_index][ich][0][::-1][0] ** 2)
                                R1 = np.sqrt(Results.ray["x" + mode_str][time_index][ich][0][::-1][40] ** 2 + Results.ray["y" + mode_str][time_index][ich][0][::-1][40] ** 2)
                                z0 = Results.ray["z" + mode_str][time_index][ich][0][::-1][0]
                                z1 = Results.ray["z" + mode_str][time_index][ich][0][::-1][40]
                                Rmin = np.min(np.sqrt(Results.ray["x" + mode_str][time_index][ich][0][::-1] ** 2 + Results.ray["y" + mode_str][time_index][ich][0][::-1] ** 2))
                            else:
                                R0 = np.sqrt(Results.ray["x" + mode_str][time_index][ich][::-1][0] ** 2 + Results.ray["y" + mode_str][time_index][ich][::-1][0] ** 2)
                                R1 = np.sqrt(Results.ray["x" + mode_str][time_index][ich][::-1][40] ** 2 + Results.ray["y" + mode_str][time_index][ich][::-1][40] ** 2)
                                z0 = Results.ray["z" + mode_str][time_index][ich][::-1][0]
                                z1 = Results.ray["z" + mode_str][time_index][ich][::-1][40]
                                Rmin = np.min(np.sqrt(Results.ray["x" + mode_str][time_index][ich][::-1] ** 2 + Results.ray["y" + mode_str][time_index][ich][::-1] ** 2))
                            R = np.linspace(R0, Rmin, 100)
                            z = z0 + (R - R0) / (R1 - R0) * (z1 - z0)
                            straight_rays.append([R, z])
                        straight_rays = np.array(straight_rays)[Results.tau[time_index] > tau_threshhold]
                        if(Config.Ext_plasma != False):
                            EQ_obj = EQData(Config.shot)
                            EQ_obj.insert_slices_from_ext(Config.time, Config.plasma_dict["eq_data"], transpose=True)
                            # the matrices in the slices are Fortran ordered - hence transposition necessary
                            self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
                                                               EQ_obj=EQ_obj, Rays=rays, straight_Rays=straight_rays)
                        else:
                            self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
                                                               Rays=rays, straight_Rays=straight_rays, \
                                                               EQ_exp=Config.EQ_exp, EQ_diag=Config.EQ_diag, \
                                                               EQ_ed=Config.EQ_ed)
                    else:
                        if(Config.Ext_plasma != False):
                            EQ_obj = EQData(Config.shot)
                            EQ_obj.insert_slices_from_ext(Config.time, Config.plasma_dict["eq_data"], transpose=True)
                            # the matrices in the slices are Fortran ordered - hence transposition necessary
                            self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
                                                           EQ_obj=EQ_obj, Rays=rays)
                        else:
                            self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
                                                               Rays=rays, EQ_exp=Config.EQ_exp, EQ_diag=Config.EQ_diag, \
                                                               EQ_ed=Config.EQ_ed)
            except KeyError:
                print("No rays available")
                if(Config.Ext_plasma != False):
                    EQ_obj = EQData(Config.shot)
                    EQ_obj.insert_slices_from_ext(Config.time, Config.plasma_dict["eq_data"], transpose=True)
                    # the matrices in the slices are Fortran ordered - hence transposition necessary
                    self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, EQ_obj=EQ_obj)
                else:
                    self.fig = self.pc_obj.Plot_Rz_Res(Config.shot, time, R_cold, z_cold, R_warm, z_warm, \
                                                               EQ_exp=Config.EQ_exp, EQ_diag=Config.EQ_diag, \
                                                               EQ_ed=Config.Eq_ed)
            self.canvas.draw()
            evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)
        self.Layout()
        self.SetClientSize(self.GetEffectiveMinSize())
        return True

    def UpdateCoords(self, event):
        if event.inaxes:
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            x, y = event.xdata, event.ydata
            evt.SetStatus('x = {0:1.3e}: y = {1:1.3e}'.format(x, y))
            self.GetEventHandler().ProcessEvent(evt)

class Ray:
    def __init__(self, s, x, y, z, H, N, N_cold, Te=0, ne=0, Y=0, X=0, x_tb=0, y_tb=0, z_tb=0, \
                                                                       x_tbp1=0, y_tbp1=0, z_tbp1=0, \
                                                                       x_tbp2=0, y_tbp2=0, z_tbp2=0):
        self.s = s  # can either be 1D or 2D depending on the number of rays (first dimension)
#        print("s", s)
        self.x = x
#        print("x", x)
        self.y = y
#        print("y", y)
        self.z = z
#        print("z", z)
        self.R = np.sqrt(x ** 2 + y ** 2)
        self.phi = np.arctan(y / x) * 180.0 / np.pi
        self.x_tb = x_tb
        self.y_tb = y_tb
        self.z_tb = z_tb
        self.x_tbp1 = x_tbp1
        self.y_tbp1 = y_tbp1
        self.z_tbp1 = z_tbp1
        self.x_tbp2 = x_tbp2
        self.y_tbp2 = y_tbp2
        self.z_tbp2 = z_tbp2
        self.R_tb = 0
        self.phi_tb = 0
        self.R_tbp1 = 0
        self.phi_tbp1 = 0
        self.R_tbp2 = 0
        self.phi_tbp2 = 0
        if(type(x_tb) != int):
            self.R_tb = np.sqrt(x_tb ** 2 + y_tb ** 2)
            self.phi_tb = np.arctan(y / x) * 180.0 / np.pi
            if(type(x_tbp1) != int):
                self.R_tbp1 = np.sqrt(x_tbp1 ** 2 + y_tbp1 ** 2)
                self.phi_tbp1 = np.arctan(y_tbp1 / x_tbp1) * 180.0 / np.pi
                self.R_tbp2 = np.sqrt(x_tbp2 ** 2 + y_tbp2 ** 2)
                self.phi_tbp2 = np.arctan(y_tbp2 / x_tbp2) * 180.0 / np.pi
        self.H = H
        self.N = N
        self.N_cold = N_cold
        self.Y = Y
        self.X = X

class ECFM_GUI:
    def __init__(self):
        GUI = ECFM_GUI_App()
        if(not Phoenix):
            MainFrame = ECFM_GUI_MainFrame(GUI, 'ECRad GUI')
            MainFrame.Show(True)
        GUI.MainLoop()

# try:
Main_ECFM = ECFM_GUI()
# except Exception as e:
#    print(e)
