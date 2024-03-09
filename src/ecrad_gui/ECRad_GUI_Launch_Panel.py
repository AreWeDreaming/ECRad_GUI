'''
Created on Mar 21, 2019

@author: Severin Denk
'''
import wx
from collections import OrderedDict as od
import numpy as np
import os
from ecrad_pylib.WX_Events import NewStatusEvt, Unbound_EVT_NEW_STATUS, EVT_UPDATE_DATA, \
                                  GenerticEvt, Unbound_OMAS_LOAD_FINISHED, OMAS_LOAD_FINISHED
from ecrad_pylib.Parallel_Utils import WorkerThread
from ecrad_pylib.ECRad_Interface import get_diag_launch
from ecrad_pylib.Diag_Types import  EXT_diag, CECE_diag
from ecrad_pylib.ECRad_Scenario import ECRadScenario
from ecrad_pylib.ECRad_Config import ECRadConfig
from ecrad_gui.ECRad_GUI_Widgets import simple_label_tc, simple_label_cb, max_var_in_row, simple_label_choice
from ecrad_gui.ECRad_GUI_Dialogs import IMASSelectDialog, OMASdbSelectDialog

class LaunchPanel(wx.Panel):
    def __init__(self, parent, Scenario, working_dir):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.Notebook = Diag_Notebook(self)
        self.diag_select_panel = wx.Panel(self, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        self.diag_select_panel.sizer = wx.BoxSizer(wx.VERTICAL)
        self.diag_select_panel.SetSizer(self.diag_select_panel.sizer)
        self.diag_select_label = wx.StaticText(self.diag_select_panel, wx.ID_ANY, "Select diagnostics to model")
        self.diag_select_panel.sizer.Add(self.diag_select_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.grid = wx.GridSizer(0, 10, 0, 0)
        self.diag_cb_dict = od()
        self.Bind(OMAS_LOAD_FINISHED, self.OnOmasLoaded)
        self.working_dir = working_dir
        for Diagkey in Scenario["avail_diags_dict"]:
            self.diag_cb_dict.update({Diagkey :simple_label_cb(self.diag_select_panel, Diagkey, False)})
            self.grid.Add(self.diag_cb_dict[Diagkey], 0, \
                          wx.TOP | wx.ALL, 5)
        for Diagkey in Scenario["used_diags_dict"]:
            if(Diagkey in self.diag_cb_dict):
                self.diag_cb_dict[Diagkey].SetValue(True)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.diag_config_sizer = wx.BoxSizer(wx.VERTICAL)
        self.diag_select_panel.sizer.Add(self.grid, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.load_launch_panel = wx.Panel(self, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        self.load_launch_panel.sizer = wx.BoxSizer(wx.VERTICAL)
        self.load_from_old_button =  wx.Button(self.load_launch_panel, wx.ID_ANY, "Load launch from ECRad result/scenario")
        self.load_from_old_button.Bind(wx.EVT_BUTTON, self.LoadLaunch)
        self.load_launch_panel.sizer.Add(self.load_from_old_button, 1, wx.ALL | wx.EXPAND, 5)
        self.gen_ext_from_raylaunch_button =  wx.Button(self.load_launch_panel, wx.ID_ANY, "Import launch from launch file")
        self.gen_ext_from_raylaunch_button.Bind(wx.EVT_BUTTON, self.GenExtFromRaylaunch)
        self.load_launch_panel.sizer.Add(self.gen_ext_from_raylaunch_button, 1, wx.ALL | wx.EXPAND, 5)
        self.load_from_omas_button =  wx.Button(self.load_launch_panel, wx.ID_ANY, "Load launch from OMAS")
        self.load_from_omas_button.Bind(wx.EVT_BUTTON, self.OnLoadOMAS)
        self.load_launch_panel.sizer.Add(self.load_from_omas_button, 1, wx.ALL | wx.EXPAND, 5)
        self.load_from_imas_button =  wx.Button(self.load_launch_panel, wx.ID_ANY, "Load launch from IMAS")
        self.load_from_imas_button.Bind(wx.EVT_BUTTON, self.OnLoadFromIMAS)
        self.load_launch_panel.sizer.Add(self.load_from_imas_button, 1, wx.ALL | wx.EXPAND, 5)
        self.gen_ext_from_old_button =  wx.Button(self.load_launch_panel, wx.ID_ANY, "Generate Ext launch from ECRad result")
        self.gen_ext_from_old_button.Bind(wx.EVT_BUTTON, self.OnGenExtFromOld)
        self.load_launch_panel.sizer.Add(self.gen_ext_from_old_button, 1, wx.ALL | wx.EXPAND, 5)
        self.diag_config_sizer.Add(self.diag_select_panel, 0, wx.ALL | wx.EXPAND, 5)
        self.load_launch_panel.SetSizer(self.load_launch_panel.sizer)
        self.Notebook.Spawn_Pages(Scenario["avail_diags_dict"])
        self.diag_config_sizer.Add(self.Notebook, 0, wx.ALL | wx.LEFT, 5)
        self.sizer.Add(self.diag_config_sizer,0, wx.EXPAND | wx.ALL,5)
        self.sizer.Add(self.load_launch_panel,1, wx.TOP | wx.ALL,5)
        self.SetSizer(self.sizer)
        self.new_data_available = False

    def OnUpdate(self, evt):
        self.SetScenario(evt.Results.Scenario, os.path.dirname(evt.path))

    def RecreateNb(self):
        self.Notebook.DeleteAllPages()
        self.Notebook.PageList = []

    def GetCurScenario(self):
        Scenario = ECRadScenario(noLoad=True)
        Scenario["avail_diags_dict"] = self.Notebook.UpdateDiagDict(Scenario["avail_diags_dict"], False)
        for Diagkey in self.diag_cb_dict:
            if(self.diag_cb_dict[Diagkey].GetValue()):
                Scenario["used_diags_dict"].update({Diagkey : Scenario["avail_diags_dict"][Diagkey]})
        return Scenario

    def UpdateScenario(self, Scenario):
        Scenario.diags_set = False
        Scenario["avail_diags_dict"] = self.Notebook.UpdateDiagDict(Scenario["avail_diags_dict"], False)
        Scenario["used_diags_dict"] = od()
        for Diagkey in self.diag_cb_dict:
            if(self.diag_cb_dict[Diagkey].GetValue()):
                Scenario["used_diags_dict"].update({Diagkey : Scenario["avail_diags_dict"][Diagkey]})
        if(len(Scenario["used_diags_dict"]) == 0):
            print("No diagnostics Selected")
            return Scenario
        if(len(Scenario["time"]) == 0):
            # No time points yet, only updating diag info
            return Scenario
        gy_dict = {}
        ECI_dict = {}
        for diag_key in Scenario["used_diags_dict"]:
            if("CT" in diag_key or "IEC" == diag_key):
                import Get_ECRH_Config
                new_gy = Get_ECRH_Config.get_ECRH_viewing_angles(Scenario["shot"], \
                                                Scenario["used_diags_dict"][diag_key].beamline, \
                                                Scenario["used_diags_dict"][diag_key].base_freq_140)
                if(new_gy.error == 0):
                    gy_dict[str(Scenario["used_diags_dict"][diag_key].beamline)] = new_gy
                else:
                    print("Error when reading viewing angles")
                    print("Launch aborted")
                    evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
                    evt.SetStatus('Error while preparing launch!')
                    self.GetEventHandler().ProcessEvent(evt)
                    return Scenario
                del(Get_ECRH_Config) # Need to destroy this here otherwise we cause an incompatability with libece
            elif(diag_key in ["ECN", "ECO", "ECI"]):
                from Shotfile_Handling_AUG import get_ECI_launch
                ECI_dict = get_ECI_launch(Scenario["used_diags_dict"][diag_key], Scenario["shot"])
        # Prepare the launches for each time point
        # Some diagnostics have steerable LOS, hence each time point has an individual launch
        for sub_key in Scenario["diagnostic"].keys():
            Scenario["diagnostic"][sub_key] = []
        try:
            for time in Scenario["time"]:
                ray_launch = get_diag_launch(Scenario["shot"], time, Scenario["used_diags_dict"], \
                                             gy_dict=gy_dict, ECI_dict=ECI_dict)
                for sub_key in Scenario["diagnostic"].keys():
                    Scenario["diagnostic"][sub_key].append(ray_launch[sub_key])
            for sub_key in Scenario["diagnostic"].keys():
                Scenario["diagnostic"][sub_key] = np.array(Scenario["diagnostic"][sub_key])
        except IOError as e:
            print(e)
            return Scenario
        Scenario.diags_set = True
        return Scenario

    def SetScenario(self, Scenario, working_dir):
        self.new_data_available = True
        self.working_dir = working_dir
        for Diagkey in self.diag_cb_dict:
            self.diag_cb_dict[Diagkey].SetValue(False)
            if(Diagkey in Scenario["used_diags_dict"]):
                self.diag_cb_dict[Diagkey].SetValue(True)
        self.Notebook.DistributeInfo(Scenario)
        
    def LoadLaunch(self, evt):
        dlg = wx.FileDialog(\
            self, message="Choose a preexisting calculation", \
            defaultDir=self.working_dir, \
            wildcard=("Matlab and Netcdf4 files (*.mat;*.nc)|*.mat;*.nc"),
            style=wx.FD_OPEN)
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            NewScenario = ECRadScenario(noLoad=True)
            NewScenario.load(filename=path)
            self.SetScenario(NewScenario, os.path.dirname(path))


    def OnLoadOMAS(self, evt):
        try:
            from omas.omas_machine import machine_to_omas
            from omas import ODS
        except ImportError:
            print("Failed to import OMAS. OMAS is an optional dependency and needs to be installed manually.")
            return
        try:
            self.Config = self.Parent.Parent.config_panel.UpdateConfig(ECRadConfig())
            self.Parent.Parent.config_panel.DisableExtRays()
        except ValueError as e:
            print("Failed to parse Configuration")
            print("Reason: " + e)
            return
#         try:
#             Scenario = self.Parent.Parent.launch_panel.UpdateScenario(self.Scenario)
#         except ValueError as e:
#             print("Failed to parse Configuration")
#             print("Reason: " + e)
#             return
        omas_db_dlg = OMASdbSelectDialog(self, minimal=True)
        if(omas_db_dlg.ShowModal() != wx.ID_OK):
            omas_db_dlg.Destroy()
            return
        state = omas_db_dlg.state
        omas_db_dlg.Destroy()
        if state[0]:
            file_dlg = wx.FileDialog(self, message="Choose a .pkl or .nc file for input", \
                                     defaultDir=self.Config["Execution"]["working_dir"], \
                                     wildcard=("Matlab and Netcdf4 files (*.pkl;*.nc)|*.pkl;*.nc"),
                                     style=wx.FD_OPEN)
            if(file_dlg.ShowModal() != wx.ID_OK):
                file_dlg.Destroy()
                return
            path = file_dlg.Path
            file_dlg.Destroy()
            WorkerThread(self.load_omas_from_file, [path])
        else:
            WorkerThread(self.load_omas_from_db, [state])

    def load_omas_from_file(self, args):
        from omas import ODS
        ods = ODS()
        file_path = args[0]
        ods.load(file_path, consistency_check="warn")
        evt_out = GenerticEvt(Unbound_OMAS_LOAD_FINISHED, self.GetId())
        evt_out.insertData(ods)
        wx.PostEvent(self, evt_out)

    def load_omas_from_db(self, args):
        from omas.omas_machine import machine_to_omas
        from omas import ODS
        ods = ODS()
        state = args[0]
        if state[1] != "d3d":
            print("Only DIII-D machine mappings supported at the moment")
            return
        machine_to_omas(ods, state[1], state[2], "ece")
        evt_out = GenerticEvt(Unbound_OMAS_LOAD_FINISHED, self.GetId())
        evt_out.insertData(ods)
        wx.PostEvent(self, evt_out)

    def OnOmasLoaded(self, evt):
        ods = evt.Data
        NewSceario = ECRadScenario(noLoad=True)
        NewSceario.set_up_launch_from_omas(ods)
        newExtDiag = EXT_diag("EXT")
        try:
            if(len( ods['ece.channel.0.time']) == 1):
                itime = 0
            else:
                timepoint_dlg = Select_Raylaunch_timepoint(self, ods['ece.channel.0.time'])
                if(not (timepoint_dlg.ShowModal() == wx.ID_OK)):
                    print("Aborted")
                    return
                itime = timepoint_dlg.itime
        except Exception as e:
            print("ERROR: Failed to load launch from OMAS")
            print(e)
            return
        newExtDiag.set_from_scenario_diagnostic(NewSceario["diagnostic"], itime, set_only_EXT=False)
        curScenario = self.GetCurScenario()
        curScenario["avail_diags_dict"].update({"EXT": newExtDiag})
        curScenario["used_diags_dict"].update({"EXT": newExtDiag})
        self.SetScenario(curScenario, self.working_dir)

    def OnLoadFromIMAS(self, evt):
        dlg = IMASSelectDialog(self, "ECE IDS source", database='ITER_MD', shot=150601, run=11)
        if(dlg.ShowModal() == wx.ID_OK):
            db = dlg.db
            check = db.open()
            if check[0] != 0:
                print('ERROR: Could not open the IMAS file with plasma')
                return
            try:
                ece_ids = db.get('ece')
            except Exception as e:
                print(e)
                print("ERROR: Cannot access ECE in IDS")
                return
            NewSceario = ECRadScenario(noLoad=True)
            try:
                NewSceario.set_up_launch_from_imas(ece_ids)
                newExtDiag = EXT_diag("EXT")
                if(len( ece_ids.channel[0].time) == 0):
                    itime = 0
                else:
                    timepoint_dlg = Select_Raylaunch_timepoint(self, ece_ids.channel[0].time)
                    if(not (timepoint_dlg.ShowModal() == wx.ID_OK)):
                        print("Aborted")
                        return
                    itime = timepoint_dlg.itime
            except Exception as e:
                print("ERROR: Failed to load launch from IMAS!")
                print("ERROR: There are probably required entries missing in the IDS")
                print(e)
                return
            newExtDiag.set_from_scenario_diagnostic(NewSceario["diagnostic"], itime, set_only_EXT=False)
            NewSceario["avail_diags_dict"].update({"EXT": newExtDiag})
            curScenario = self.GetCurScenario()
            curScenario["avail_diags_dict"].update({"EXT": newExtDiag})
            curScenario["used_diags_dict"].update({"EXT": newExtDiag})
            self.SetScenario(curScenario, self.working_dir)
        dlg.Destroy()

    def OnGenExtFromOld(self, evt):
        dlg = wx.FileDialog(\
            self, message="Choose a preexisting calculation", \
            defaultDir=self.working_dir, \
            wildcard=("Matlab and Netcdf4 files (*.mat;*.nc)|*.mat;*.nc"),
            style=wx.FD_OPEN)
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            NewSceario = ECRadScenario(noLoad=True)
            NewSceario.load(filename=path)
            newExtDiag = EXT_diag("EXT")
            if(len(NewSceario["time"]) == 1):
                itime = 0
            else:
                timepoint_dlg = Select_Raylaunch_timepoint(self, NewSceario["time"])
                if(not (timepoint_dlg.ShowModal() == wx.ID_OK)):
                    print("Aborted")
                    return
                itime = timepoint_dlg.itime
            newExtDiag.set_from_scenario_diagnostic(NewSceario["diagnostic"], itime, set_only_EXT=False)
            NewSceario["avail_diags_dict"].update({"EXT":  newExtDiag})
            curScenario = self.GetCurScenario()
            curScenario["avail_diags_dict"].update({"EXT":  newExtDiag})
            curScenario["used_diags_dict"].update({"EXT":  newExtDiag})
            self.SetScenario(curScenario, self.working_dir) 
    
    def GenExtFromRaylaunch(self, evt):
        dlg = wx.FileDialog(\
            self, message="Choose a file with raylaunch data", \
            defaultDir=self.working_dir, \
            wildcard=("Matlab and Netcdf4 files (*.mat;*.nc)|*.mat;*.nc"),
            style=wx.FD_OPEN)
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            newExtDiag = EXT_diag("EXT")
            ext = os.path.splitext(path)[1]
            if(ext == ".mat"):
                newExtDiag.set_from_mat(path)
            elif(ext == ".nc"):
                newExtDiag.set_from_NETCDF(path)
            else:
                raise ValueError("Only .mat and .nc files are supported")
            curScenario = self.GetCurScenario()
            curScenario["avail_diags_dict"].update({"EXT":  newExtDiag})
            curScenario["used_diags_dict"].update({"EXT":  newExtDiag})
            self.SetScenario(curScenario, self.working_dir)  

    def UpdateNeeded(self):
        check_list = []
        if(self.new_data_available):
            return True
        for Diagkey in self.diag_cb_dict:
            if(self.diag_cb_dict[Diagkey].CheckForNewValue()):
                return True
            if(self.diag_cb_dict[Diagkey].GetValue()):
                check_list.append(Diagkey)
        if(len(check_list) == 0):
            return True
        return  self.Notebook.CheckForNewValues(check_list)

class Diag_Notebook(wx.Choicebook):
    def __init__(self, parent):
        wx.Choicebook.__init__(self, parent, wx.ID_ANY, \
                            style=wx.BK_DEFAULT)
        self.PageDict = od()

    def Spawn_Pages(self, DiagDict) :
        self.varsize = (0, 0)
        for diag in DiagDict:
            self.PageDict.update({diag : Diag_Page(self, DiagDict[diag])})
            pagename = diag
            if(len(pagename) > 10 and ' ' in pagename):
                pagelist = pagename.split(' ')
                pagename = ""
                last = 0
                for j in range(len(pagelist)):
                    if(int(len(pagename) / 10) > last):
                        pagelist[j] = pagelist[j] + '\n'
                        last += 1
                    else:
                        pagelist[j] = pagelist[j] + ' '
                    pagename = pagename + pagelist[j]
                if(pagename.endswith('\n') or pagename.endswith(' ')):
                    pagename = pagename[0:len(pagename) - 1]
            self.AddPage(self.PageDict[diag], pagename)

    def UpdateDiagDict(self, DiagDict, used=True):
        for diag in self.PageDict:
            DiagDict[diag] = self.PageDict[diag].RetrieveDiag(used)
        return DiagDict

    def DistributeInfo(self, Scenario):
        for diag in self.PageDict:
            if(self.PageDict[diag].name in Scenario["used_diags_dict"]):
                self.PageDict[diag].DepositDiag(Scenario["used_diags_dict"][self.PageDict[diag].name])
            else:
                self.PageDict[diag].DepositDiag(Scenario["avail_diags_dict"][self.PageDict[diag].name])
                

    def CheckForNewValues(self, check_list):
        for diag in check_list:
            if(self.PageDict[diag].CheckForNewValues()):
                return True
        return False

class Diag_Page(wx.Panel):
    def __init__(self, parent, Diag_obj, border=1, maxwidth=max_var_in_row, \
                    parentmode=False, style=wx.TAB_TRAVERSAL | wx.NO_BORDER):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=style)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        if(type(Diag_obj) == EXT_diag):
            self.diagpanel = ExtDiagPanel(self, Diag_obj)
        elif( type(Diag_obj) == CECE_diag):
            self.diagpanel = CECEDiagPanel(self, Diag_obj)
        else:
            self.diagpanel = Diag_Panel(self, Diag_obj)
        self.name = Diag_obj.name
        self.sizer.Add(self.diagpanel, 0, wx.ALL | wx.TOP, 5)

    def RetrieveDiag(self, used=True):
        self.diag = self.diagpanel.GetDiag(used)
        return self.diag

    def DepositDiag(self, diag):
        self.diagpanel.SetDiag(diag)

    def CheckForNewValues(self):
        return self.diagpanel.CheckForNewValues()

class Diag_Panel(wx.Panel):
    def __init__(self, parent, Diag_obj):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        self.Diag = Diag_obj
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.grid_sizer = wx.GridSizer(0, 4, 0, 0)
        self.art_data_beamline = 1
        self.art_data_base_freq_140 = True
        self.art_data_pol_coeff_X = 1.0
        self.art_data_pol_launch = 0.0
        self.art_data_tor_launch = 0.0
        self.widget_dict = {}
        self.selected_channel = 0
        for attribute in Diag_obj.properties:
            if(Diag_obj.data_types_dict[attribute] != "bool"):
                scale = None
                if(attribute in Diag_obj.scale_dict):
                    scale = Diag_obj.scale_dict[attribute]
                self.widget_dict[attribute] = simple_label_tc(self, Diag_obj.descriptions_dict[attribute], \
                                                              getattr(Diag_obj, attribute), \
                                                              Diag_obj.data_types_dict[attribute], \
                                                              scale=scale)
            else:
                self.widget_dict[attribute] = simple_label_cb(self, Diag_obj.descriptions_dict[attribute], \
                                                              getattr(Diag_obj, attribute))
            self.grid_sizer.Add(self.widget_dict[attribute], 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.sizer.Add(self.grid_sizer, 0, wx.ALIGN_LEFT | wx.ALL, 5)
        self.SetSizer(self.sizer)

    def GetDiag(self, used=True):
        for attribute in self.Diag.properties:
            setattr(self.Diag, attribute, self.widget_dict[attribute].GetValue())
        return self.Diag

    def SetDiag(self, Diag):
        self.Diag = Diag
        for attribute in self.Diag.properties:
            self.widget_dict[attribute].SetValue(getattr(self.Diag, attribute))

    def CheckForNewValues(self):
        for attribute in self.Diag.properties:
            if(self.widget_dict[attribute].CheckForNewValue()):
                return True
        return False

class CECEDiagPanel(Diag_Panel):
    def __init__(self, parent, Diag_obj):
        Diag_Panel.__init__(self, parent, Diag_obj)
        self.load_f_button = wx.Button(self, wx.ID_ANY, label="Load CECE frequecies")
        self.load_f_button.Bind(wx.EVT_BUTTON, self.OnLoadF)
        self.sizer.Add(self.load_f_button, 0, wx.ALIGN_LEFT | wx.ALL, 5)

    def OnLoadF(self, evt):
        dlg = wx.FileDialog(\
            self, message="Choose a file with values", \
            wildcard=("Single column text file (*txt)|*.txt"),
            style=wx.FD_OPEN)
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            dlg.Destroy()
            try:
                values = np.loadtxt(path)
            except Exception as e:
                print("ERROR:: Failed to load file because ", e)
                return
            if(values.ndim != 2):
                print("ERROR:: Can only use single column values")
                print("INFO:: Shape from text file ", values.shape)
                return
            self.Diag.f = values.T[0]
            self.Diag.df = values.T[1]
            print("INFO:: Frequencies set sucessfully!")
        else:
            dlg.Destroy()

    def GetDiag(self, used=True):
        if(self.Diag.f is None and used):
            raise ValueError("Warning! You need to set the CECE frequencies before you can run ECRad")
        return Diag_Panel.GetDiag(self, used)

class ExtDiagPanel(Diag_Panel):
    def __init__(self, parent, Diag_obj):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        self.Diag = Diag_obj
        self.art_data_beamline = 1
        self.art_data_base_freq_140 = True
        self.art_data_pol_coeff_X = 1.0
        self.art_data_pol_launch = 0.0
        self.art_data_tor_launch = 0.0
        self.widget_dict = {}
        self.selected_channel = 0
        self.NewValues = False
        self.launch_edit_sizer = wx.GridBagSizer(vgap=5, hgap=5)
        quantities = []
        default_value = None
        for prop in self.Diag.properties:
            if(prop != "N_ch"):
                quantities.append(Diag_obj.descriptions_dict[prop])
                if(default_value is None):
                    default_value = (getattr(self.Diag, prop) * self.Diag.scale_dict[prop])[0]
        self.quant_choice = simple_label_choice(self, "Quantity to edit", quantities, quantities[0])
        self.launch_edit_sizer.Add(self.quant_choice, (0,0), (1,2), 
                flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)
        self.override_value_tc = simple_label_tc(self, "Replace with", default_value, "real")
        self.launch_edit_sizer.Add(self.override_value_tc, (0,2), (1,1), 
                flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)
        self.override_value_button = wx.Button(self, label="Set value for all channels")
        self.override_value_button.Bind(wx.EVT_BUTTON, self.OnOverrideAll)
        self.launch_edit_sizer.Add(self.override_value_button, (0,4), (1,2), 
                flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)
        self.min_value_tc = simple_label_tc(self, "Start value", default_value, "real")
        self.launch_edit_sizer.Add(self.min_value_tc, (1,2), (1,1), 
                flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)
        self.max_value_tc = simple_label_tc(self, "Stop value", default_value, "real")
        self.launch_edit_sizer.Add(self.max_value_tc, (1,3), (1,1), 
                flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)
        self.set_from_range_button = wx.Button(self, label="Set channels from range")
        self.set_from_range_button.Bind(wx.EVT_BUTTON, self.OnSetLinspace)
        self.launch_edit_sizer.Add(self.set_from_range_button, (1,4), (1,2), 
                flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_VERTICAL, border=5)
        self.from_file_buton = wx.Button(self, label="Set channels from file")
        self.from_file_buton.Bind(wx.EVT_BUTTON, self.OnSetFromFile)
        self.launch_edit_sizer.Add(self.from_file_buton, (2,4), (1,2), 
                flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.launch_edit_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 5)
        self.grid_sizer = wx.GridSizer(0, 4, 0, 0)
        N_ch = getattr(Diag_obj, "N_ch")
        self.widget_dict["N_ch"] = simple_label_tc(self, Diag_obj.descriptions_dict["N_ch"], \
                                                   getattr(Diag_obj, "N_ch"), \
                                                   Diag_obj.data_types_dict["N_ch"])
        self.grid_sizer.Add(self.widget_dict["N_ch"], 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.channel_ctrl_sizer = wx.BoxSizer(wx.VERTICAL)
        self.channel_select_ch = wx.Choice(self, wx.ID_ANY)
        self.channel_select_ch.AppendItems(np.array(range(1, N_ch + 1), dtype="|U3").tolist())
        self.channel_select_ch.SetSelection(self.selected_channel)
        self.channel_select_ch.Bind(wx.EVT_CHOICE, self.OnNewChannelSelected)
        self.channel_ctrl_sizer.Add(self.channel_select_ch, 0, wx.EXPAND | wx.ALL, 5)
        self.update_N_ch_Button = wx.Button(self, label='Update Channel Number')
        self.update_N_ch_Button.Bind(wx.EVT_BUTTON, self.OnUpdateNch)
        self.channel_ctrl_sizer.Add(self.update_N_ch_Button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        self.grid_sizer.Add(self.channel_ctrl_sizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        for attribute in Diag_obj.properties:
            if(attribute == "N_ch"):
                continue
            if(Diag_obj.data_types_dict[attribute] != "bool"):
                scale = None
                if(attribute in Diag_obj.scale_dict):
                    scale = Diag_obj.scale_dict[attribute]
                self.widget_dict[attribute] = simple_label_tc(self, Diag_obj.descriptions_dict[attribute], \
                                                              getattr(Diag_obj, attribute)[self.selected_channel], \
                                                              Diag_obj.data_types_dict[attribute], \
                                                              scale=scale)
            else:
                self.widget_dict[attribute] = simple_label_cb(self, Diag_obj.descriptions_dict[attribute], \
                                                              getattr(Diag_obj, attribute))
            self.grid_sizer.Add(self.widget_dict[attribute], 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.sizer.Add(self.grid_sizer, 0, wx.ALL | wx.LEFT, 5)
        self.SetSizer(self.sizer)

    def SetNewNch(self, N_ch):
        if(N_ch < self.Diag.N_ch):
            if(self.selected_channel > N_ch):
                self.selected_channel = N_ch - 1
        # Shorten current channel list
            for attribute in self.Diag.properties:
                if(attribute == "N_ch"):
                    continue
                temp = np.copy(getattr(self.Diag, attribute))
                new_vals = np.zeros(N_ch)
                new_vals[:] = temp[0:N_ch]
                setattr(self.Diag, attribute, new_vals)
        elif(N_ch > self.Diag.N_ch):
        # Extend list
            for attribute in self.Diag.properties:
                if(attribute == "N_ch"):
                    continue
                temp = np.copy(getattr(self.Diag, attribute))
                new_vals = np.zeros(N_ch)
                new_vals[:] = temp[0]  # Use first channel as default for the new ones
                new_vals[0:self.Diag.N_ch] = temp[:]
                setattr(self.Diag, attribute, new_vals)
        setattr(self.Diag, "N_ch", N_ch)
        self.channel_select_ch.Clear()
        self.channel_select_ch.AppendItems(np.array(range(1, N_ch + 1), dtype="|U3").tolist())
        self.channel_select_ch.Select(self.selected_channel)  # note not channel number but channel index, i.e. ch no. 1 -> 0
        self.NewValues = True

    def OnUpdateNch(self, evt):
        if(self.widget_dict["N_ch"].GetValue() == self.Diag.N_ch):
            return
        N_ch = self.widget_dict["N_ch"].GetValue()
        self.SetNewNch(N_ch)

    def OnNewChannelSelected(self, evt):
        old_selected_channel = self.selected_channel
        self.selected_channel = self.channel_select_ch.GetSelection()
        for attribute in self.Diag.properties:
            if(self.widget_dict[attribute].CheckForNewValue()):
                self.NewValues = True
            if(attribute == "N_ch"):
                    continue
            vals = getattr(self.Diag, attribute)
            vals[old_selected_channel] = self.widget_dict[attribute].GetValue()
            setattr(self.Diag, attribute, vals)
            self.widget_dict[attribute].SetValue(getattr(self.Diag, attribute)[self.selected_channel])

    def GetDiag(self, used=True):
        self.channel_select_ch.SetSelection(0)
        self.OnNewChannelSelected(None)
        self.NewValues = False
        return self.Diag

    def SetDiag(self, Diag):
        self.channel_select_ch.Clear()
        self.channel_select_ch.AppendItems(np.array(range(1, Diag.N_ch + 1), dtype="|U3").tolist())
        self.channel_select_ch.SetSelection(0)
        self.Diag = Diag
        self.widget_dict["N_ch"].SetValue(self.Diag.N_ch)
        for attribute in self.Diag.properties:
            setattr(self.Diag, attribute,  getattr(self.Diag, attribute))
            if(attribute == "N_ch"):
                self.widget_dict[attribute].SetValue(getattr(self.Diag, attribute))
            else:
                self.widget_dict[attribute].SetValue(getattr(self.Diag, attribute)[0])
        self.NewValues = False

    def CheckForNewValues(self):
        if(self.NewValues):
            return self.NewValues
        return Diag_Panel.CheckForNewValues(self)

    def SetDiagValues(self, key, values):
        setattr(self.Diag, key, values)
        self.SetDiag(self.Diag)

    def OnOverrideAll(self, evt):
        # + 1 because we removed N_ch
        key = self.Diag.properties[self.quant_choice.GetSelection() + 1]
        values = np.zeros(self.Diag.N_ch)
        values[:] =  self.override_value_tc.GetValue() / self.Diag.scale_dict[key]
        self.SetDiagValues(key, values)

    def OnSetLinspace(self, evt):
        # + 1 because we removed N_ch
        key = self.Diag.properties[self.quant_choice.GetSelection() + 1]
        values = np.linspace(self.min_value_tc.GetValue() / self.Diag.scale_dict[key], 
                             self.max_value_tc.GetValue() / self.Diag.scale_dict[key],
                             self.Diag.N_ch)
        self.SetDiagValues(key, values)

    def OnSetFromFile(self, evt):
        dlg = wx.FileDialog(\
            self, message="Choose a file with values", \
            wildcard=("Single column text file (*txt)|*.txt"),
            style=wx.FD_OPEN)
        if(dlg.ShowModal() == wx.ID_OK):
            path = dlg.GetPath()
            dlg.Destroy()
            try:
                values = np.loadtxt(path)
            except Exception as e:
                print("ERROR:: Failed to load file because ", e)
                return
        else:
            dlg.Destroy()
            return
        if(values.ndim != 1):
            print("ERROR:: Can only use single column values")
            print("INFO:: Shape from text file ", values.shape)
            return
        # + 1 because we removed N_ch
        key = self.Diag.properties[self.quant_choice.GetSelection() + 1]
        self.SetNewNch(len(values))
        self.SetDiagValues(key, values / self.Diag.scale_dict[key])

class Select_Raylaunch_timepoint(wx.Dialog):
    def __init__(self, parent, time_list):
        wx.Dialog.__init__(self, parent, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.time_ctrl = wx.ListBox(self, wx.ID_ANY)
        for time in time_list:
            self.time_ctrl.Append("{0:1.4f}".format(time))
        self.time_ctrl.Select(0)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.FinishButton = wx.Button(self, wx.ID_ANY, 'Accept')
        self.Bind(wx.EVT_BUTTON, self.EvtAccept, self.FinishButton)
        self.DiscardButton = wx.Button(self, wx.ID_ANY, 'Discard')
        self.Bind(wx.EVT_BUTTON, self.EvtClose, self.DiscardButton)
        self.ButtonSizer.Add(self.DiscardButton, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.ButtonSizer.Add(self.FinishButton, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.sizer.Add(self.time_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.ButtonSizer)

    def EvtClose(self, Event):
        self.EndModal(wx.ID_ABORT)

    def EvtAccept(self, Event):
        self.itime = self.time_ctrl.GetSelection()
        self.EndModal(wx.ID_OK)

