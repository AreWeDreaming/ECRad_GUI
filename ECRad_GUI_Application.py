# -*- coding: utf-8 -*-
import os
import wx
import sys
from glob import glob
library_list = glob("../*pylib") + glob("../*PyLib")
found_lib = False
ECRadPylibFolder = None
for folder in library_list:
    if("ECRad" in folder or "ecrad" in folder):
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
if(globalsettings.AUG):
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
from WX_Events import EVT_NEW_STATUS, EVT_RESIZE, LoadMatEvt, Unbound_EVT_LOAD_OLD_RESULT, \
                      EVT_MAKE_ECRAD, EVT_NEXT_TIME_STEP, EVT_UPDATE_CONFIG, \
                      EVT_UPDATE_DATA, EVT_LOCK_EXPORT, EVT_GENE_DATA_LOADED, EVT_LOAD_OLD_RESULT, \
                      NewStatusEvt, Unbound_EVT_NEW_STATUS, \
                      Unbound_EVT_MAKE_ECRAD, GENEDataEvt, Unbound_EVT_GENE_DATA_LOADED, \
                      UpdateDataEvt, Unbound_EVT_UPDATE_DATA, UpdateConfigEvt, \
                      Unbound_EVT_UPDATE_CONFIG, Unbound_EVT_NEXT_TIME_STEP,\
                      Unbound_EVT_ECRAD_FINISHED, ProccessFinishedEvt, \
                      EVT_ECRAD_FINISHED, \
                      Unbound_EVT_LOAD_ECRAD_RESULT,EVT_LOAD_ECRAD_RESULT, \
                      Unbound_EVT_ECRAD_RESULT_LOADED, EVT_ECRAD_RESULT_LOADED,\
    ThreadFinishedEvt
from ECRad_GUI_Shell import Redirect_Text
from ECRad_Interface import prepare_input_files
from ECRad_Results import ECRadResults
from Parallel_Utils import WorkerThread
from multiprocessing import Process, Queue, Pipe
from ECRad_Execution import SetupECRadBatch
import queue
from ECRad_F2PY_Interface import ECRadF2PYInterface
import getpass
from ECRad_GUI_PlotPanel import PlotPanel
from subprocess import Popen
ECRad_Model = False
from time import sleep
from io import StringIO
# Events


def kill_handler(signum, frame):
    print('Successfully terminated ECRad with Signal ', signum)

class ECRad_GUI_App(wx.App):
    def __init__(self, ECRad_runner_process, ECRad_input_queue, ECRad_output_queue):
        """
        Initialise the App.
        """
        self.ECRad_runner_process = ECRad_runner_process
        self.ECRad_input_queue = ECRad_input_queue
        self.ECRad_output_queue = ECRad_output_queue
        wx.App.__init__(self)

    def OnInit(self):
        self.SetAppName("ECRad GUI")
        if(globalsettings.Phoenix):
            frame = ECRad_GUI_MainFrame(self, 'ECRad GUI', self.ECRad_runner_process, \
                                        self.ECRad_input_queue, self.ECRad_output_queue)
            self.SetTopWindow(frame)
            frame.Show(True)
        return True

class ECRad_GUI_MainFrame(wx.Frame):
    def __init__(self, parent, title, ECRad_runner_process, ECRad_input_queue, ECRad_output_queue):
        wx.Frame.__init__(self, None, wx.ID_ANY, title, \
                          style=wx.DEFAULT_FRAME_STYLE | \
                          wx.FULL_REPAINT_ON_RESIZE)
        self.FrameParent = parent
        self.statusbar = self.CreateStatusBar(2)  # , wx.ST_SIZEGRIP
        self.statusbar.SetStatusWidths([-2, -1])
        self.Bind(EVT_NEW_STATUS, self.SetNewStatus)
        self.Bind(EVT_RESIZE, self.OnResizeAll)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)
        self.CreateMenuBar()
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ECRad_runner_process = ECRad_runner_process
        self.ECRad_input_queue = ECRad_input_queue
        self.Panel = Main_Panel(self, ECRad_runner_process, ECRad_input_queue, ECRad_output_queue)
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
            wildcard=("Matlab and Netcdf4 files (*.mat;*.nc)|*.mat;*.nc"),
            style=wx.FD_OPEN)
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            dlg.Destroy()
            evt = LoadMatEvt(Unbound_EVT_LOAD_OLD_RESULT, self.Panel.GetId())
            evt.SetFilename(path)
            self.Panel.GetEventHandler().ProcessEvent(evt)

    def OnQuit(self, event):
        self.ECRad_input_queue.put(["close", None, None])
        self.ECRad_runner_process.join()
        self.ECRad_runner_process.close()
        self.FrameParent.ExitMainLoop()
        self.Destroy()

    def OnResizeAll(self, evt):
        self.Layout()
        self.Refresh()

class Main_Panel(scrolled.ScrolledPanel):
    def __init__(self, parent, ECRad_runner_process, ECRad_input_queue, ECRad_output_queue):
        scrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY)
        self.parent = parent
        self.ECRad_running = False
        self.ECRad_runner_process = ECRad_runner_process
        self.ECRad_input_queue = ECRad_input_queue
        self.ECRad_output_queue = ECRad_output_queue
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.Results = ECRadResults(lastused=True)
        self.Bind(EVT_MAKE_ECRAD, self.OnProcessTimeStep)
        self.Bind(EVT_ECRAD_FINISHED, self.OnProcessEnded)
        self.Bind(EVT_NEXT_TIME_STEP, self.OnNextTimeStep)
        self.Bind(EVT_UPDATE_CONFIG, self.OnConfigLoaded)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.Bind(EVT_LOCK_EXPORT, self.OnLockExport)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(EVT_GENE_DATA_LOADED, self.OnGeneLoaded)
        self.Bind(EVT_ECRAD_RESULT_LOADED, self.OnResultsImported)
        self.Bind(EVT_LOAD_OLD_RESULT, self.OnImport)
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
        self.ExportButton = wx.Button(self, wx.ID_ANY, 'Save results')
        if(globalsettings.Phoenix):
            self.ExportButton.SetToolTip("If this is grayed out there is no (new) data to save!")
        else:
            self.ExportButton.SetToolTipString("If this is grayed out there is no (new) data to save!")
        self.ExportButton.Bind(wx.EVT_BUTTON, self.OnExport)
        self.ExportButton.Disable()
        self.NameButton = wx.Button(self, wx.ID_ANY, 'Comment Results')
        self.NameButton.Bind(wx.EVT_BUTTON, self.OnName)
        username = "."
        if(getpass.getuser() in ["sdenk", "g2sdenk", "denk"]):
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
        self.ButtonSizer.Add(self.ExportButton, 0, wx.ALL | \
                        wx.LEFT, 5)
        self.ButtonSizer.Add(self.NameButton, 0, wx.ALL | \
                        wx.LEFT, 5)
        
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
        self.Progress_sizer.Add(self.Progress_label, 0, wx.ALL, 5)
        self.Redirector = Redirect_Text(self.Log_Box)
        sys.stdout = self.Redirector
        self.index = 0  # Index for the iteration over timepoints
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
        self.sizer.Add(self.UpperBook, 1, wx.ALL | \
            wx.LEFT, 5)

#     def __del__(self):
#         if self.ECRad_process is not None:
#             self.ECRad_process.Detach()
#             self.ECRad_process.CloseOutput()
#             self.ECRad_process = None

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
        if(self.Results.Config["Physics"]["dstf"] not in ["Th", "Re", "Lu", "Ge", "GB"]):
            print("Invalid choice of distribution")
            print("Possible options:")
            print("Th -> thermal plasma")
            print("Re -> distribution function computed by RELAX")
            print("Lu -> distribution function computed by LUKE (deprecated)")
            print("Ge, GB -> distribution function computed by GENE (deprecated)")
            print("Please select a valid distribution function identifier.")
            return
        scenario_updated = False
        # Reset only the result fields but leave Scenario and Config untouched
        self.Results.reset(light=True)
        # Sets time points and stores plasma data in Scenario
        if(self.scenario_select_panel.FullUpdateNeeded() or not self.Results.Scenario.plasma_set):
            try:
                self.Results.Scenario = self.scenario_select_panel.UpdateScenario(self.Results.Scenario, self.Results.Config, None)
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
            for t in self.Results.Scenario["time"]:
                self.TimeBox.Append("{0:1.4f}".format(t))
            scenario_updated = True
        else:
            self.Results.Scenario = self.scenario_select_panel.SetScaling(self.Results.Scenario)
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
        self.Results.Scenario.set_up_dimensions()
        # Stores launch data in Scenario
        self.stop_current_evaluation = False
        self.index = 0
        old_comment = self.Results.comment
        self.Results.comment = old_comment # Keep the comment
        if(len(list(self.Results.Scenario["used_diags_dict"].keys())) == 0):
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
            self.FinalECRadSetup(scenario_updated)
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
        if(self.Results.Scenario.load_GENE_obj(pathname, self.Results.Config["Physics"]["dstf"])):
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
                    wx.PostEvent(self, evt)
                    return
                if(not self.Results.Scenario.integrate_GeneData(np.asarray(gene_dlg.used, dtype=np.float) * 1.e-3)):
                    print("GENE object not properly initialized - this is most likely due to a bug in the GUI")
                    evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                    evt.SetStatus('')
                    wx.PostEvent(self, evt)
                    return
                evt_out_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
                evt_out_2.SetResults(self.Results)
                wx.PostEvent(self.scenario_select_panel, evt_out_2)
                gene_dlg.Destroy()
                self.TimeBox.Clear()
                for time in self.Results.Scenario["time"]:
                    self.TimeBox.Append("{0:1.5f}".format(time))
                self.FinalECRadSetup(True)
            else:
                print("Aborted")
                evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                evt.SetStatus('')
                wx.PostEvent(self, evt)
                return
        else:
            print("Error when loading GENE data - see above")
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('')
            wx.PostEvent(self, evt)
            return         

    def FinalECRadSetup(self, scenario_updated):
        # Thinga we need to do just before we get going
        if(scenario_updated):
                self.Results.Scenario.autosave()
        self.Results.set_dimensions()
        self.ProgressBar.SetRange(self.Results.Scenario["dimensions"]["N_time"])
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('ECRad is running - please wait.')
        wx.PostEvent(self, evt)
        self.Progress_label.SetLabel("ECRad running - ({0:d}/{1:d})".format(self.index + 1,len(self.Results.Scenario["time"])))
        self.ProgressBar.SetValue(self.index)
        self.ExportButton.Disable()
        self.NameButton.Disable()
        self.StartECRadButton.Disable()
        evt = wx.PyCommandEvent(Unbound_EVT_MAKE_ECRAD, self.GetId())
        wx.PostEvent(self, evt)

    def OnProcessTimeStep(self, evt):
        self.ECRad_running = True
        self.ECRad_input_queue.put(["run ECRad", self.Results, self.index]) 
        
    def ECRadRunner(cls, input_queue, output_queue):
        ECRad_inferface = ECRadF2PYInterface()
        while True:
            args = input_queue.get()
            try:
                command = args[0]
                if(command == "close"):
                    break
                Results = args[1]
                if(Results.Config["Execution"]["batch"]):
                    scratch_dir = Results.Config["Execution"]["scratch_dir"]
                    Results.Scenario.to_netcdf(filename=os.path.join(scratch_dir, "Scenario.nc"))
                    Results.Config.to_netcdf(filename=os.path.join(scratch_dir, "Config.nc"))
                    run_ECRad = SetupECRadBatch(Results.Config, Results.Scenario, Results.Scenario["time"][args[2]])
                    ECRad_batch = Popen(run_ECRad)
                    ECRad_batch.wait()
                    try:
                        filename, ed = Results.get_default_filename_and_edition(True)
                        NewResults = ECRadResults(False)
                        NewResults.from_netcdf(filename)
                        NewResults.to_netcdf()
                        output_queue.put([True, NewResults])
                    except:
                        print("Failed to run remotely. Please check .o and .e files at")
                        print(scratch_dir)
                        output_queue.put([False, Results])
                else:
                    Results = ECRad_inferface.process_single_timepoint(Results, args[2])
                    output_queue.put([True, Results])
            except Exception as e:
                print(e)
                output_queue.put([False, Results])
    
    ECRadRunner = classmethod(ECRadRunner)
    
            
    def OnProcessEnded(self, evt):
        self.ECRad_running = False
        if(evt.success):
            if(self.Results.Config["Execution"]["batch"]):
                self.index = self.Results.Scenario["dimensions"]["N_time"]
            # Append times twice to track which time points really do have results in case of crashes
            self.index += 1
        else:
            if(self.Results.Config["Execution"]["batch"]):
                # If batch crashes we have to dump everything
                self.index = 0
                while self.index < self.Results.Scenario["dimensions"]["N_time"]:
                    self.Results.Scenario.drop_time_point(self.index)
            else:
                print("Sorry, ECRad crashed. Please send the log console output to Severin Denk")
                print("Skipping current time point {0:1.4f} and continuing".format(self.Results.Scenario["time"][self.index]))
                self.Results.Scenario.drop_time_point(self.index)
                self.ProgressBar.SetRange(self.Results.Scenario["dimensions"]["N_time"])
        if(self.index < len(self.Results.Scenario["time"]) and not self.stop_current_evaluation):
            evt = NewStatusEvt(Unbound_EVT_NEXT_TIME_STEP, self.GetId())
            wx.PostEvent(self, evt)
        else:
            self.FinishUpECRad()
                        
    def OnNextTimeStep(self, evt):
        if(not self.stop_current_evaluation):
            evt = wx.PyCommandEvent(Unbound_EVT_MAKE_ECRAD, self.GetId())
            wx.PostEvent(self, evt)
        else:
            self.FinishUpECRad()
            
    def FinishUpECRad(self):
        if(self.Results.Scenario["dimensions"]["N_time"] == 0):
            # Unsuccessful termination
            print("None of the ECRad runs were completed succesfully - sorry")
            self.Results = ECRadResults()
            # We have deleted all entries from the Scenario we need to rebuilt this
            self.Results.Scenario.plasma_set = False
            self.Progress_label.SetLabel("No ECRad run in progress")
            self.ProgressBar.SetRange(1)
            self.ProgressBar.SetValue(1)
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            evt.SetStatus('ECRad failed - sorry!')
            self.GetEventHandler().ProcessEvent(evt)
            self.stop_current_evaluation = True
            self.StartECRadButton.Enable()
            return
        if(not self.Results.Config["Execution"]["batch"]):
            # Remove time points in case of early termination
            for i in range(self.index, self.Results.Scenario["dimensions"]["N_time"]):
                self.Results.Scenario.drop_time_point(i)
            self.Results.tidy_up(False)
        self.TimeBox.Clear()
        for t in self.Results.Scenario["time"]:
            self.TimeBox.Append("{0:1.4f}".format(t))
        self.KillECRadButton.Disable()
        self.stop_current_evaluation = False
        self.ExportButton.Enable()
        self.NameButton.Enable()
        self.Progress_label.SetLabel("No ECRad run in progress")
        self.ProgressBar.SetRange(self.index)
        self.ProgressBar.SetValue(self.index)
        evt = wx.PyCommandEvent()
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('ECRad has Finished!')
        wx.PostEvent(self, evt)
        if(not self.Results.Config["Execution"]["batch"]):
            print("Now saving results")
            print("This takes a moment please wait")
            WorkerThread(self.SavingThread, [])
        evt_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
        evt_2.SetResults(self.Results)
        if(globalsettings.AUG):
            wx.PostEvent(self.calib_panel, evt)
            self.calib_panel.GetEventHandler().ProcessEvent(evt_2)
        wx.PostEvent(self.scenario_select_panel, evt_2)
        wx.PostEvent(self.plot_panel, evt_2)
        self.StartECRadButton.Enable()
        
    def SavingThread(self, args):
        try:
            self.Results.autosave()
        except Exception as e:
            print("ERROR: Failed to save results")
            print(e)

    def OnKillECRad(self, evt):
        self.stop_current_evaluation = True
        print("Waiting for current calculation to finish")
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Termination scheduled - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        self.KillECRadButton.Disable()
    

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
        self.ExportButton.Enable()
        self.NameButton.Enable()
        print("Updated main results")

    def OnImport(self, evt):
        self.Results = ECRadResults()
        print("Now loarding: " + evt.filename)
        print("This takes a moment please wait")
        WorkerThread(self.ImportThread, [evt.filename])
        
    def ImportThread(self,args):
        evt = ThreadFinishedEvt(Unbound_EVT_ECRAD_RESULT_LOADED, self.GetId())
        try:
            self.Results.load(args[0])
            evt.SetSuccess(True)
        except Exception as e:
            print(e)
            evt.SetSuccess(False)
        wx.PostEvent(self, evt)
        
    def OnResultsImported(self, evt):
        if(evt.success):
            print("Results loaded")
            self.DiagBox.Clear()
            for diag_key in self.Results.Scenario["used_diags_dict"]:
                self.DiagBox.Append(diag_key)
            self.TimeBox.Clear()
            for time in self.Results.Scenario["time"]:
                self.TimeBox.Append("{0:1.5f}".format(time))
            evt_out = UpdateConfigEvt(Unbound_EVT_UPDATE_CONFIG, self.GetId())
            wx.PostEvent(self,evt_out)
            evt_out_2 = UpdateDataEvt(Unbound_EVT_UPDATE_DATA, self.GetId())
            evt_out_2.SetResults(self.Results)
            if(globalsettings.AUG):
                wx.PostEvent(evt_out_2, self.calib_panel)
            wx.PostEvent(self.scenario_select_panel, evt_out_2)
            wx.PostEvent(self.plot_panel, evt_out_2)
        else:
            print("ERROR: Failed to load Results")

    def OnExport(self, evt):
        try:
            try:
                NewConfig = self.config_panel.UpdateConfig(self.Results.Config)
                self.Results.Config["Execution"]["working_dir"] = NewConfig["Execution"]["working_dir"]
            except ValueError as e:
                print("Failed to parse Configuration")
                print("Reason: ", e)
                print("Did not update working directory")
            if(self.Results is not None):
                WorkerThread(self.Results.to_netcdf)
            else:
                print("No results to save")
        except AttributeError as e:
            print("No results to save")
            print(e)
        except IOError as e:
            print("Failed to save results")
            print(e)

    def OnLockExport(self, evt):
        self.ExportButton.Disable()
        self.NameButton.Disable()

    def OnIdle(self, evt):
        if(self.ECRad_running):
            try:
                success, self.Results = self.ECRad_output_queue.get(block=False)
                evt = ProccessFinishedEvt(Unbound_EVT_ECRAD_FINISHED, self.GetId())
                evt.SetSuccess(success)
                wx.PostEvent(self, evt)
                return
            except queue.Empty:
                pass
            if(not self.ECRad_runner_process.is_alive()):
                self.ECRad_runner_process = Process(target=Main_Panel.ECRadRunner, \
                                                    args=(self.ECRad_input_queue, \
                                                          self.ECRad_output_queue))
                self.ECRad_runner_process.start()
                success = False
                evt = ProccessFinishedEvt(Unbound_EVT_ECRAD_FINISHED, self.GetId())
                evt.SetSuccess(success)
                wx.PostEvent(self, evt)

#         if(self.ECRad_process is not None):
#             stream = self.ECRad_process.GetInputStream()
#             if stream is not None:
#                 if stream.CanRead():
#                     text = stream.read()
#                     self.Log_Box.AppendText(text)
#             evt.RequestMore()
#         elif(self.ECRad_running):
#             print("ECRad seems to have crashed without the corresponding event chain firing")
#             print("This might cause some weird stuff from here on out")
#             print("Trying to fix it...")
#             self.ECRad_running = False
#             self.OnProcessEnded(None) 

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
        # Redirect stdout from ECRad
        ECRad_input_queue = Queue()
        ECRad_output_queue = Queue()
        ECRad_runner_process = Process(target=Main_Panel.ECRadRunner, args=(ECRad_input_queue,ECRad_output_queue))
        ECRad_runner_process.start()
        GUI = ECRad_GUI_App(ECRad_runner_process, ECRad_input_queue, ECRad_output_queue)
        GUI.MainLoop()

if __name__ == '__main__':
    Main_ECRad = ECRad_GUI()
# except Exception as e:
#    print(e)
