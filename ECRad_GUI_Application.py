# -*- coding: utf-8 -*-
import os
import wx
import sys
from glob import glob
from ECRad_GUI_Thread import WorkerThread
library_list = glob("../*pylib") + glob("../*Pylib")
found_lib = False
ECRadPylibFolder = None
for folder in library_list:
    if("ECRad" in folder or "ecrad"in folder ):
        sys.path.append(os.path.abspath(folder))
        found_lib = True
        ECRadPylibFolder = folder
        break
if(not found_lib):
    print("Could not find pylib")
    print("Important: ECRad_GUI must be launched with its home directory as the current working directory")
    print("Additionally, the ECRad_Pylib must be in the parent directory of the GUI and must contain one of ECRad, ecrad and Pylib or pylib")
    exit(-1)
from Global_Settings import globalsettings
globalsettings.ECRadGUIRoot = os.getcwd()
globalsettings.ECRadPylibRoot = ECRadPylibFolder
try:
    import Equilibrium_Utils_AUG
except (OSError,ModuleNotFoundError):
    globalsettings.AUG = False
    print("Failed to load AUG libraries continuing in non-AUG mode.")
import wx.lib.scrolledpanel as scrolled
from ECRad_GUI_LaunchPanel import LaunchPanel
from ECRad_GUI_ScenarioPanel import ScenarioSelectPanel
from ECRad_GUI_Config_Panel import ConfigPanel
from ECRad_GUI_Calibration_Suite import CalibPanel, CalibEvolutionPanel
from ECRad_GUI_Dialogs import Select_GENE_timepoints_dlg
# import  wx.lib.scrolledpanel as ScrolledPanel
import numpy as np
from WX_Events import EVT_NEW_STATUS, EVT_RESIZE, LoadMatEvt, Unbound_EVT_LOAD_MAT, \
                      EVT_MAKE_ECRAD, EVT_NEXT_TIME_STEP, EVT_UPDATE_CONFIG, \
                      EVT_UPDATE_DATA, EVT_LOCK_EXPORT, EVT_GENE_DATA_LOADED, EVT_LOAD_MAT, \
                      NewStatusEvt, Unbound_EVT_NEW_STATUS, \
                      Unbound_EVT_MAKE_ECRAD, GENEDataEvt, Unbound_EVT_GENE_DATA_LOADED, \
                      UpdateDataEvt, Unbound_EVT_UPDATE_DATA, UpdateConfigEvt, \
                      Unbound_EVT_UPDATE_CONFIG, Unbound_EVT_NEXT_TIME_STEP
from ECRad_GUI_Shell import Redirect_Text
from ECRad_Interface import prepare_input_files, GetECRadExec
from ECRad_Results import ECRadResults
import getpass
from ECRad_GUI_PlotPanel import PlotPanel
ECRad_Model = False
from time import sleep
# Events


def kill_handler(signum, frame):
    print('Successfully terminated ECRad with Signal ', signum)



class ECRad_GUI_App(wx.App):
    def OnInit(self):
        self.SetAppName("ECRad GUI")
        if(globalsettings.Phoenix):
            frame = ECRad_GUI_MainFrame(self, 'ECRad GUI')
            self.SetTopWindow(frame)
            frame.Show(True)
        return True

class ECRad_GUI_MainFrame(wx.Frame):
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

        # if(ECRad_Model):
        #    self.ECRad_Ext_window = ECRad_Ext.ECRad_GUI_ECRad_Ext_Frame(self)
        #    self.ECRad_Ext_window.Show()
        #    self.ECRad_Ext_window.Raise()
        #    self.ECRad_Ext_window.Center()
        self.SetSizer(self.sizer)
#        self.SetClientSize(self.Panel.sizer.GetMinSize())
#        self.PlotWindow = PlotFrame(self)
        width = min(wx.GetDisplaySize()[0] * 0.8, 1680)
        height = min(wx.GetDisplaySize()[1] * 0.8, 960)
        self.SetClientSize((width, height))
        self.Center()


    def SetNewStatus(self, evt):
        self.statusbar.SetStatusText(evt.Status)

    def CreateMenuBar(self):
        self._menuBar = wx.MenuBar(wx.MB_DOCKABLE)
        self._fileMenu = wx.Menu()
        self._editMenu = wx.Menu()
        self.ECRad_config_load = wx.MenuItem(self._fileMenu, wx.ID_ANY, text=\
            "Load preexisting calculation")
        self.Hide_Config = wx.MenuItem(self._fileMenu, wx.ID_ANY, text=\
            'Hide the Input Mask')
        self.Show_Config = wx.MenuItem(self._fileMenu, wx.ID_ANY, text=\
            'Show the Input Mask')
        self.ECRad_quit = wx.MenuItem(self._fileMenu, wx.ID_ANY, \
                                "&Close\tCtrl-Q", "Close ECRad_GUI")
        if(globalsettings.Phoenix):
            self._fileMenu.Append(self.ECRad_config_load)
            self._fileMenu.Append(self.ECRad_quit)
        else:
            self._fileMenu.AppendItem(self.ECRad_config_load)
            self._fileMenu.AppendItem(self.ECRad_quit)
        self._menuBar.Append(self._fileMenu, "&File")
        # self._fileMenu.AppendItem(self.Hide_Config)
        # self._fileMenu.AppendItem(self.Show_Config)
        self.SetMenuBar(self._menuBar)
        self.Bind(wx.EVT_MENU, self.OnOpenOldFile, self.ECRad_config_load)
        self.Bind(wx.EVT_MENU, self.OnHideConfig, self.Hide_Config)
        self.Bind(wx.EVT_MENU, self.OnShowConfig, self.Show_Config)
        self.Bind(wx.EVT_MENU, self.OnQuit, self.ECRad_quit)
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
            defaultDir=self.Panel.Results .Config["Execution"]["working_dir"], \
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

class Main_Panel(scrolled.ScrolledPanel):
    def __init__(self, parent):
        scrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY)
        self.parent = parent
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.ECRad_running = False
        self.ECRad_process = None
        self.ECRad_pid = None
        self.stop_current_evaluation = False
        self.Results = ECRadResults(lastused=True)
        self.Results.Config
        self.Bind(EVT_MAKE_ECRAD, self.OnProcessTimeStep)
        self.Bind(wx.EVT_END_PROCESS, self.OnProcessEnded)
        self.Bind(EVT_NEXT_TIME_STEP, self.OnNextTimeStep)
        self.Bind(EVT_UPDATE_CONFIG, self.OnConfigLoaded)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.Bind(EVT_LOCK_EXPORT, self.OnLockExport)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(EVT_GENE_DATA_LOADED, self.OnGeneLoaded)
        self.SetSizer(self.sizer)
        self.SetSize((400, 400))
        self.SetMinSize((400, 400))
        self.data = None
        self.ControlSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ButtonSizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.ControlSizer, 0, wx.EXPAND | wx.ALL , 5)
        self.StartECRadButton = wx.Button(self, wx.ID_ANY, \
            'Start ECRad')
        self.KillECRadButton = wx.Button(self, wx.ID_ANY, 'Terminate ECRad')
        self.StartECRadButton.Bind(wx.EVT_BUTTON, self.OnStartECRad)
        self.KillECRadButton.Bind(wx.EVT_BUTTON, self.OnKillECRad)
        self.KillECRadButton.Disable()
        self.ExporttoMatButton = wx.Button(self, wx.ID_ANY, 'Export to .mat')
        if(globalsettings.Phoenix):
            self.ExporttoMatButton.SetToolTip("If this is grayed out there is no (new) data to save!")
        else:
            self.ExporttoMatButton.SetToolTipString("If this is grayed out there is no (new) data to save!")
        self.ExporttoMatButton.Bind(wx.EVT_BUTTON, self.OnExporttoMat)
        self.ExporttoMatButton.Disable()
        self.NameButton = wx.Button(self, wx.ID_ANY, 'Comment Results')
        self.NameButton.Bind(wx.EVT_BUTTON, self.OnName)
        self.Bind(EVT_LOAD_MAT, self.OnImportMat)
        username = "."
        if(getpass.getuser() in ["sdenk", "g2sdenk", "denk"]):
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
        self.ButtonSizer.Add(self.StartECRadButton, 0, wx.ALL | \
                        wx.LEFT, 5)
        self.ButtonSizer.Add(self.KillECRadButton, 0, wx.ALL | \
                        wx.LEFT, 5)
        self.ButtonSizer.Add(self.ExporttoMatButton, 0, wx.ALL | \
                        wx.LEFT, 5)
        self.ButtonSizer.Add(self.NameButton, 0, wx.ALL | \
                        wx.LEFT, 5)
        
#        if(getpass.getuser() == "sdenk"):
#            self.ButtonSizer.Add(self.ExporttoNssfButton, 0, wx.ALL | \
#                        wx.LEFT, 5)
#            self.ButtonSizer.Add(self.ExporttotokpNssfButton, 0, wx.ALL | \
#                        wx.LEFT, 5)
        self.ControlSizer.Add(self.ButtonSizer, 0, wx.ALIGN_TOP)
        self.Log_Box = wx.TextCtrl(self, wx.ID_ANY, size=(200, 100), \
                style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.Log_Box.AppendText('Welcome to the ECRad GUI' + username + os.linesep)
        self.diag_box_sizer = wx.BoxSizer(wx.VERTICAL)
        self.diag_box_label = wx.StaticText(self, wx.ID_ANY, "Diagnostics")
        self.DiagBox = wx.ListBox(self, wx.ID_ANY, size=(100, 100))
        for diag_key in list(self.Results.Scenario["used_diags_dict"]):
            self.DiagBox.Append(diag_key)
        self.diag_box_sizer.Add(self.diag_box_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL , 5)
        self.diag_box_sizer.Add(self.DiagBox, 1, wx.ALL | wx.EXPAND , 5)
        self.time_box_sizer = wx.BoxSizer(wx.VERTICAL)
        self.time_box_label = wx.StaticText(self, wx.ID_ANY, "Time points")
        self.TimeBox = wx.ListBox(self, wx.ID_ANY, size=(100, 100))
        for time in self.Results.Scenario["time"]:
            self.TimeBox.Append("{0:1.5f}".format(time))
        self.time_box_sizer.Add(self.time_box_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL , 5)
        self.time_box_sizer.Add(self.TimeBox, 1, wx.ALL | wx.EXPAND , 5)
        self.ControlSizer.Add(self.Log_Box, 1, wx.ALL | wx.EXPAND , 5)
        self.ControlSizer.Add(self.diag_box_sizer, 0, wx.ALL | wx.EXPAND, 5)
        self.ControlSizer.Add(self.time_box_sizer, 0, wx.ALL | wx.EXPAND, 5)
        self.ProgressBar = wx.Gauge(self, wx.ID_ANY, style=wx.GA_HORIZONTAL)
        self.Progress_label = wx.StaticText(self, wx.ID_ANY, "No ECRad run in progress")
        self.Progress_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.Progress_sizer.Add(self.ProgressBar, 1, wx.ALL | wx.EXPAND, 5)
        self.Progress_sizer.Add(self.Progress_label, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        self.Redirector = Redirect_Text(self.Log_Box)
        sys.stdout = self.Redirector
        self.InvokeECRad = None
        self.index = 0  # Index for the iteration over timepoints
        self.DoReflecOnly = False  # Only evaluate the reflection model in the next time step
        self.UpperBook = wx.Notebook(self)
        self.scenario_select_panel = ScenarioSelectPanel(self.UpperBook, self.Results.Scenario, self.Results.Config)
        self.UpperBook.AddPage(self.scenario_select_panel, "Select IDA time points")
        self.launch_panel = LaunchPanel(self.UpperBook, self.Results.Scenario, self.Results.Config["Execution"]["working_dir"])
        self.UpperBook.AddPage(self.launch_panel, "Diagnostic configuration")
        self.config_panel = ConfigPanel(self.UpperBook, self.Results.Config)
        self.UpperBook.AddPage(self.config_panel, "ECRad configuration")
        self.plot_panel = PlotPanel(self.UpperBook)
        self.UpperBook.AddPage(self.plot_panel, "Misc. Plots")
        self.sizer.Add(self.Progress_sizer, 0, wx.ALL | wx.EXPAND, 5)
        self.SetScrollRate(20, 20)
        if(globalsettings.AUG):
            self.calib_panel = CalibPanel(self.UpperBook, self.Results.Scenario)
            self.UpperBook.AddPage(self.calib_panel, "ECRad Calibration")
            self.calib_evolution_Panel = CalibEvolutionPanel(self.UpperBook, self.Results.Config["Execution"]["working_dir"])
            self.UpperBook.AddPage(self.calib_evolution_Panel, "Plotting for calibration")
        else:
            print("AUG shotfile system inaccessible -> Cross calibration disabled")
        self.sizer.Add(self.UpperBook, 1, wx.ALL | \
            wx.LEFT, 5)

    def __del__(self):
        if self.ECRad_process is not None:
            self.ECRad_process.Detach()
            self.ECRad_process.CloseOutput()
            self.ECRad_process = None

    # Overwrite this to stop the window from constantly jumping
    def OnChildFocus(self, evt):
        pass

    def OnStartECRad(self, evt):
        if(self.ECRad_running):
            print('ECRad is still running - please wait!')
            return
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Preparing run - GUI might be unresponsive for minutes - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        try:
            self.Results.Config = self.config_panel.UpdateConfig(self.Results.Config)
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: ", e)
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('')
            self.GetEventHandler().ProcessEvent(evt)
            return
        if(self.Results.Config["dstf"] not in ["Th", "Re", "Lu", "Ge", "GB"]):
            print("Invalid choice of distribution")
            print("Possible options:")
            print("Th -> thermal plasma")
            print("Re -> distribution function computed by RELAX")
            print("Lu -> distribution function computed by LUKE (deprecated)")
            print("Ge, GB -> distribution function computed by GENE (deprecated)")
            print("Please select a valid distribution function identifier.")
            return
        scenario_updated = False
        # Sets time points and stores plasma data in Scenario
        if(self.scenario_select_panel.FullUpdateNeeded() or not self.Results.Scenario.plasma_set):
            try:
                self.Results.Scenario = self.scenario_select_panel.LoadScenario(self.Results.Scenario, self.Results.Config, None)
                if(not self.Results.Scenario.plasma_set):
                    evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                    evt.SetStatus('')
                    self.GetEventHandler().ProcessEvent(evt)
                    return
            except ValueError as e:
                print("Failed to load Scenario")
                print("Reason: ", e)
                evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                evt.SetStatus('')
                self.GetEventHandler().ProcessEvent(evt)
                return
            self.TimeBox.Clear()
            for t in self.Results.Scenario.plasma_dict["time"]:
                self.TimeBox.Append("{0:1.4f}".format(t))
            scenario_updated = True
        else:
            self.Results.Scenario = self.scenario_select_panel.SetScaling(self.Results.Scenario)
        # Stores launch data in Scenario
        if(self.launch_panel.UpdateNeeded() or not self.Results.Scenario.diags_set):
            try:
                self.Results.Scenario = self.launch_panel.UpdateScenario(self.Results.Scenario)
                if(not self.Results.Scenario.diags_set):
                    evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                    evt.SetStatus('')
                    self.GetEventHandler().ProcessEvent(evt)
                    return
            except ValueError as e:
                print("Failed to parse diagnostic info")
                print("Reason: ", e)
                evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                evt.SetStatus('')
                self.GetEventHandler().ProcessEvent(evt)
                return
            self.DiagBox.Clear()
            for diag in list(self.Results.Scenario["used_diags_dict"]):
                self.DiagBox.Append(diag)
            scenario_updated = True
        self.stop_current_evaluation = False
        self.index = 0
        old_comment = self.Results.comment
        self.Results.reset()
        self.Results.comment = old_comment # Keep the comment
        if(len(list(self.Results.Scenario["used_diags_dict"])) == 0):
            print("No diagnostics selected")
            print("Run aborted")
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('')
            self.GetEventHandler().ProcessEvent(evt)
            return
        if(len(self.Results.Scenario["time"]) == 0):
            print("No time points selected")
            print("Run aborted")
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('')
            self.GetEventHandler().ProcessEvent(evt)
            return
        if(self.Results.Config["Physics"]["dstf"] == "Re"):
            if(self.Results.Scenario["dist_obj"] is None):
                fileDialog=wx.FileDialog(self, "Selectr file with bounce averaged distribution data", \
                                                     defaultDir = self.Results.Config["Execution"]["working_dir"], \
                                                     wildcard="matlab files (*.mat)|*.mat",
                                                     style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
                if(fileDialog.ShowModal() == wx.ID_CANCEL):
                    print("Launch aborted")
                    return
                else:
                    pathname = fileDialog.GetPath()
                    self.Results.Scenario.load_dist_obj(pathname)
                    fileDialog.Destroy()
        self.Results.Config.autosave()
        if(self.Results.Config["Physics"]["dstf"] not in ["Ge", "GB"]):
            if(scenario_updated):
                self.Results.Scenario.autosave()
            self.ProgressBar.SetRange(len(self.Results.Scenario["time"]))
            evt = wx.PyCommandEvent(Unbound_EVT_MAKE_ECRAD, self.GetId())
            wx.PostEvent(self, evt)
        else:
            if(len(self.Results.Scenario["time"]) != 1):
                print("For GENE distributions please select only one time point, i.e. the time point of the gene calcuation")
                evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                evt.SetStatus('')
                self.GetEventHandler().ProcessEvent(evt)
                return
            fileDialog=wx.FileDialog(self, "Selectr file with GENE distribution data", \
                                                 defaultDir = self.Results.Config["Execution"]["working_dir"], \
                                                 wildcard="hdf5 files (*.h5)|*.h5",
                                                 style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
            if(fileDialog.ShowModal() == wx.ID_CANCEL):
                print("Launch aborted")
                return
            else:
                pathname = fileDialog.GetPath()
                WorkerThread(self.LoadGeneData, [pathname])
                fileDialog.Destroy()
            
    def LoadGeneData(self, args):
        pathname = args[0]
        evt = GENEDataEvt(Unbound_EVT_GENE_DATA_LOADED, wx.ID_ANY)
        if(self.Results.Scenario.load_GENE_obj(pathname, self.Results.Config["dstf"])):
            evt.set_state(0)
        else:
            evt.set_state(-1)
        wx.PostEvent(self, evt)
     
    def OnGeneLoaded(self, evt):
        if(evt.state == 0):
            gene_dlg = Select_GENE_timepoints_dlg(self, self.Results.Scenario["GENE_obj"].time)
            if(gene_dlg.ShowModal() == wx.ID_OK):
                if(len(gene_dlg.used) == 0):
                    print("No time point selected")
                    evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                    evt.SetStatus('')
                    self.GetEventHandler().ProcessEvent(evt)
                    return
                if(not self.Results.Scenario.integrate_GeneData(np.asarray(gene_dlg.used, dtype=np.float) * 1.e-3)):
                    print("GENE object not properly initialized - this is most likely due to a bug in the GUI")
                    evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                    evt.SetStatus('')
                    self.GetEventHandler().ProcessEvent(evt)
                    return
                evt_out_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
                evt_out_2.SetResults(self.Results)
                wx.PostEvent(self.scenario_select_panel, evt_out_2)
                gene_dlg.Destroy()
                self.TimeBox.Clear()
                for time in self.Results.Scenario["time"]:
                    self.TimeBox.Append("{0:1.5f}".format(time))
                self.ProgressBar.SetRange(len(self.Results.Scenario["time"]))
                self.Results.Scenario.autosave()
                evt = wx.PyCommandEvent(Unbound_EVT_MAKE_ECRAD, self.GetId())
                wx.PostEvent(self, evt)
            else:
                print("Aborted")
                evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                evt.SetStatus('')
                self.GetEventHandler().ProcessEvent(evt)
                return
        else:
            print("Error when loading GENE data - see above")
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('')
            self.GetEventHandler().ProcessEvent(evt)
            return
            
            
    def OnProcessTimeStep(self, evt):
        if(os.path.isfile(os.path.join(self.Results.Config["Execution"]["working_dir"], "ECRad.out"))):
            os.remove(os.path.join(self.Results.Config["Execution"]["working_dir"], "ECRad.out"))
        if(os.path.isfile(os.path.join(self.Results.Config["Execution"]["working_dir"], "ECRad.err"))):
            os.remove(os.path.join(self.Results.Config["Execution"]["working_dir"], "ECRad.err"))
        if(not prepare_input_files(self.Results.Config, self.Results.Scenario, self.index, \
                                   ext_result = self.scenario_select_panel.Result_for_ext_launch)):
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
        self.NameButton.Disable()
        try:
            self.InvokeECRad = GetECRadExec(self.Results.Config, self.Results.Scenario, self.Results.Scenario["time"][self.index])
        except ValueError:
            print("Something wrong with the job submission configuration!")
            return
        os.environ['ECRad_WORKING_DIR'] = self.Results.Config["Execution"]["working_dir"]
        self.Progress_label.SetLabel("ECRad running - ({0:d}/{1:d})".format(self.index + 1,len(self.Results.Scenario["time"])))
        self.ProgressBar.SetValue(self.index)
        self.ECRad_process = wx.Process(self)
        self.ECRad_process.Redirect()
        print("-------- Launching ECRad -----------\n")
        print("-------- INVOKE COMMAND------------\n")
        print(self.InvokeECRad)
        print("-------- Current working directory ------------\n")
        print(os.getcwd())
        print("-----------------------------------\n")
        self.StartECRadButton.Disable()
#            ticket_manager = wx.Process(self)
#            ticket_manager_pid = wx.Execute("echo $KRB5CCNAME", \
#                                       wx.EXEC_SYNC, ticket_manager)
        self.ECRad_pid = wx.Execute(self.InvokeECRad, \
                                    wx.EXEC_ASYNC, self.ECRad_process)
        self.ECRad_running = True
        if(self.Results.Config["parallel"] and not self.Results.Config["batch"]):
            while(not wx.Process.Exists(self.ECRad_pid)):
                sleep(0.25)
            os.system("renice -n 10 -p " + "{0:d}".format(self.ECRad_process.GetPid()) + " >/dev/null 2>&1")
        self.KillECRadButton.Enable()
#        print InvokeECRad + EOLCHART
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('ECRad has launched - please wait.')
        self.GetEventHandler().ProcessEvent(evt)


    def OnUpdate(self, evt):
        self.Results = evt.Results
        self.DiagBox.Clear()
        for diag_key in list(self.Results.Scenario["used_diags_dict"]):
            self.DiagBox.Append(diag_key)
        self.TimeBox.Clear()
        for time in self.Results.Scenario["time"]:
            self.TimeBox.Append("{0:1.5f}".format(time))
        evt_out = UpdateConfigEvt(Unbound_EVT_UPDATE_CONFIG, self.GetId())
        self.GetEventHandler().ProcessEvent(evt_out)
        self.ExporttoMatButton.Enable()
        self.NameButton.Enable()
        print("Updated main results")

    def OnImportMat(self, evt):
        self.Results = ECRadResults()
        self.Results.from_mat_file(evt.filename)
        self.DiagBox.Clear()
        for diag_key in self.Results.Scenario["used_diags_dict"]:
            self.DiagBox.Append(diag_key)
        self.TimeBox.Clear()
        for time in self.Results.Scenario["time"]:
            self.TimeBox.Append("{0:1.5f}".format(time))
        evt_out = UpdateConfigEvt(Unbound_EVT_UPDATE_CONFIG, self.GetId())
        self.GetEventHandler().ProcessEvent(evt_out)
        evt_out_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
        evt_out_2.SetResults(self.Results)
        if(globalsettings.AUG):
            self.calib_panel.GetEventHandler().ProcessEvent(evt_out_2)
        self.scenario_select_panel.GetEventHandler().ProcessEvent(evt_out_2)
        self.plot_panel.GetEventHandler().ProcessEvent(evt_out_2)
        print("Successfully imported:", evt.filename)

    def OnExporttoMat(self, evt):
        try:
            try:
                NewConfig = self.config_panel.UpdateConfig(self.Results.Config)
                self.Results.Config["Execution"]["working_dir"] = NewConfig["Execution"]["working_dir"]
            except ValueError as e:
                print("Failed to parse Configuration")
                print("Reason: ", e)
                print("Did not update working directory")
            if(self.Results is not None):
                self.Results.to_mat_file()
            else:
                print("No results to save")
        except AttributeError as e:
            print("No results to save")
            print(e)
        except IOError as e:
            print("Failed to save results")
            print(e)

    def OnLockExport(self, evt):
        self.ExporttoMatButton.Disable()
        self.NameButton.Disable()

    def OnNextTimeStep(self, evt):
        if(not self.stop_current_evaluation):
            evt = wx.PyCommandEvent(Unbound_EVT_MAKE_ECRAD, self.GetId())
            wx.PostEvent(self, evt)
        else:
            self.Scenario["time"] = self.Scenario["time"][0:self.index]  # shorten time array in case of early termination
            self.Results.time = self.Results.time[0:self.index]
            self.Results.tidy_up()
            self.ExporttoMatButton.Enable()
            self.NameButton.Enable()
            evt_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
            evt_2.SetResults(self.Results)
            evt_2.SetConfig(self.Results.Config)
            self.Calib_Panel.GetEventHandler().ProcessEvent(evt_2)
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('ECRad has Finished!')
            self.Progress_label.SetLabel("No ECRad run in progress")
            self.ProgressBar.SetValue(0)
            self.sizer.Layout()
            self.StartECRadButton.Enable()

    def OnKillECRad(self, evt):
        self.stop_current_evaluation = True
        print("Waiting for current calculation to finish")
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Termination scheduled - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        self.KillECRadButton.Disable()

    def OnIdle(self, evt):
        if(self.ECRad_process is not None):
            stream = self.ECRad_process.GetInputStream()
            if stream is not None:
                if stream.CanRead():
                    text = stream.read()
                    self.Log_Box.AppendText(text)
            evt.RequestMore()
        elif(self.ECRad_running):
            print("ECRad seems to have crashed without the corresponding event chain firing")
            print("This might cause some weird stuff from here on out")
            print("Trying to fix it...")
            self.ECRad_running = False
            self.OnProcessEnded(None) 

    def OnProcessEnded(self, evt):
        self.ECRad_running = False
        if(self.ECRad_process is None):
            print("ECRad model has crashed")
            print("Please read Error log above")
            self.Results = ECRadResults()
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('ECRad has crashed - sorry!')
            self.Progress_label.SetLabel("No ECRad run in progress")
            self.StartECRadButton.Enable()
            self.GetEventHandler().ProcessEvent(evt)
            return
        stream = self.ECRad_process.GetInputStream()
        if stream is not None:
            if stream.CanRead():
                text = stream.read()
                self.Log_Box.AppendText(text)
        self.ECRad_process.Destroy()
        self.ECRad_process = None
        self.ECRad_pid = None
        try:
            # Append times twice to track which time points really do have results in case of crashes
            self.Results.append_new_results(self.Results.Scenario["time"][self.index])
            self.index += 1
        except IOError as e:
            print("Results of ECRad cannot be found!")
            print("Most likely cause is an error that occurred within ECRad")
            print("Please run the ECRad with current input parameters in a separate shell.")
            print("The command to launch the ECRad can be found above.")
            print("Afterwards please send any error messages that appear at sdenk|at|ipp.mpg.de")
            print("If no errors occur make sure that you don't have another instance of ECRad GUI working in the same working directory")
            print(e)
            print("Skipping current time point {0:1.4f} and continuing".format(self.Results.Scenario["time"][self.index]))
            self.Results.Scenario["time"] = np.delete(self.Results.Scenario["time"], self.index)
            if(len(np.shape(self.Results.Scenario["plasma"]["Te"][self.index])) == 1):
                try:
                    self.Results.Scenario["plasma"]["rhop_prof"] = np.delete(self.Results.Scenario["plasma"]["rhop_prof"], self.index)
                except Exception:
                    print("No rhop profile information")
                try:
                    self.Results.Scenario["plasma"]["rhot_prof"] = np.delete(self.Results.Scenario["plasma"]["rhot_prof"], self.index)
                except Exception:
                    print("No rhot profile information")
            self.Results.Scenario["plasma"]["Te"] = np.delete(self.Results.Scenario["plasma"]["Te"], self.index)
            self.Results.Scenario["plasma"]["ne"] = np.delete(self.Results.Scenario["plasma"]["ne"], self.index)
            if(not self.Results.Scenario.use3Dscen.used):
                self.Results.Scenario.plasma_dict["eq_data"] = np.delete(self.Results.Scenario.plasma_dict["eq_data"], self.index)
            self.Results.Scenario.ray_launch = np.delete(self.Results.Scenario.ray_launch, self.index)
        except IndexError as e:
            print("Error parsing results of ECRad")
            print("Most likely cause is an error that occurred within the ECRad")
            print("Please run the ECRad with current input parameters in a separate shell.")
            print("The command to launch the ECRad can be found above.")
            print("Afterwards please send any error messages that appear at sdenk|at|ipp.mpg.de")
            print("If no errors occur make sure that you don't have another instance of ECRad GUI working in the same working directory")
            print(e)
            self.Progress_label.SetLabel("No ECRad run in progress")
            self.ProgressBar.SetRange(self.index)
            self.ProgressBar.SetValue(self.index)
            self.GetEventHandler().ProcessEvent(evt)
            self.Results = ECRadResults()  # Empty results
            self.stop_current_evaluation = True
            return
        if(self.index < len(self.Results.Scenario.plasma_dict["time"]) and not self.stop_current_evaluation):
            evt = NewStatusEvt(Unbound_EVT_NEXT_TIME_STEP, self.GetId())
            self.GetEventHandler().ProcessEvent(evt)
        else:
            # Shorten more stuff!
            if(len(self.Results.Scenario.plasma_dict["time"]) == 0):
                print("None of the ECRad runs were completed succesfully - sorry")
                self.Results = ECRadResults()
                self.Progress_label.SetLabel("No ECRad run in progress")
                self.ProgressBar.SetRange(self.index)
                self.ProgressBar.SetValue(self.index)
                self.GetEventHandler().ProcessEvent(evt)
                self.Results = ECRadResults()  # Empty results
                self.stop_current_evaluation = True
                self.StartECRadButton.Enable()
                return
            for key in self.Results.Scenario.plasma_dict:
                if(key != "vessel_bd" and key != "prof_reference"):
                    if(self.Results.Scenario.plasma_dict[key] is not None):
                        self.Results.Scenario.plasma_dict[key] = self.Results.Scenario.plasma_dict[key][0:self.index]  # shorten time array in case of early termination
            self.Results.time = np.copy(self.Results.Scenario.plasma_dict["time"])
            self.TimeBox.Clear()
            for t in self.Results.time:
                self.TimeBox.Append("{0:1.4f}".format(t))
            self.KillECRadButton.Disable()
            self.stop_current_evaluation = False
            self.Results.tidy_up()
            self.ExporttoMatButton.Enable()
            self.NameButton.Enable()
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('ECRad has Finished!')
            self.Progress_label.SetLabel("No ECRad run in progress")
            self.ProgressBar.SetRange(self.index)
            self.ProgressBar.SetValue(self.index)
            self.GetEventHandler().ProcessEvent(evt)
            evt_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
            evt_2.SetResults(self.Results)
            if(globalsettings.AUG):
                self.calib_panel.GetEventHandler().ProcessEvent(evt_2)
            self.scenario_select_panel.GetEventHandler().ProcessEvent(evt_2)
            self.plot_panel.GetEventHandler().ProcessEvent(evt_2)
            print("-------- ECRad has terminated -----------\n")
            self.StartECRadButton.Enable()

    def OnConfigLoaded(self, evt):
        self.config_panel.SetConfig(self.Results.Config)
        self.config_panel.DisableExtRays()
        self.launch_panel.SetScenario(self.Results.Scenario, self.Results.Config["Execution"]["working_dir"])
        
    def OnName(self, evt):
        if(self.Results.comment == None):
            comment = ""
        else:
            print(self.Results.comment)
            comment = self.Results.comment
        comment_dialogue = wx.TextEntryDialog(self, 'Please type comment for your calculation!', value=comment)
        if(comment_dialogue.ShowModal() == wx.ID_OK):
            self.Results.comment = comment_dialogue.GetValue()

class ECRad_GUI:
    def __init__(self):
        GUI = ECRad_GUI_App()
        if(not globalsettings.Phoenix):
            MainFrame = ECRad_GUI_MainFrame(GUI, 'ECRad GUI')
            MainFrame.Show(True)
        GUI.MainLoop()

# try:
Main_ECRad = ECRad_GUI()
# except Exception as e:
#    print(e)
