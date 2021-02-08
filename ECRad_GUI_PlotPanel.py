'''
Created on Apr 3, 2019

@author: sdenk
'''

from Global_Settings import globalsettings
import wx
import os
from ECRad_GUI_Widgets import simple_label_tc, simple_label_cb
from Plotting_Configuration import plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from Plotting_Core import PlottingCore
if(globalsettings.AUG):
    from Shotfile_Handling_AUG import shotfile_exists, get_data_calib, AUG_profile_diags,\
                                      load_IDA_data, get_Thomson_data
else:
    print("AUG shotfile system inaccessible -> Cannot plot diagnostic data!")                                
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar2Wx
import numpy as np
from TB_Communication import Ray, make_TORBEAM_no_data_load
from Parallel_Utils import WorkerThread
from Basic_Methods.Equilibrium_Utils import EQDataExt as EQData
from Diag_Types import Diag
from ECRad_GUI_Diagnostic import Diagnostic
from ECRad_Results import ECRadResults
from BDOP_3D import make_3DBDOP_cut_GUI
from Diag_Efficiency import diag_weight
from ECRH_Launcher import ECRHLauncher
from ECRad_GUI_Dialogs import TextEntryDialog
from WX_Events import EVT_UPDATE_DATA, EVT_THREAD_FINISHED, EVT_DIAGNOSTICS_LOADED, \
                      EVT_OTHER_RESULTS_LOADED, NewStatusEvt, Unbound_EVT_NEW_STATUS, \
                      Unbound_EVT_THREAD_FINISHED, UpdateDiagDataEvt, \
                      Unbound_EVT_DIAGNOSTICS_LOADED, GenerticEvt, \
                      EVT_DONE_PLOTTING, Unbound_EVT_OTHER_RESULTS_LOADED, \
                      Unbound_EVT_RESIZE,UpdatePlotEvent, Unbound_EVT_DONE_PLOTTING

class PlotPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.parent = parent
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        self.controlplotsizer = wx.BoxSizer(wx.VERTICAL)
        self.Results = None
        self.smoothing_time = 1.e-3
        self.FigureControlPanel = FigureBook(self)
        self.Bind(EVT_UPDATE_DATA, self.OnUpdate)
        self.Bind(EVT_OTHER_RESULTS_LOADED, self.OnOtherResultsLoaded)
        self.controlgrid = wx.BoxSizer(wx.HORIZONTAL)
        self.controlgrid2 = wx.BoxSizer(wx.HORIZONTAL)
        self.lb_widgets = {}
        self.multiple = {}
        self.time_sizer = wx.BoxSizer(wx.VERTICAL)
        self.time_label = wx.StaticText(self, wx.ID_ANY, "time [s]")
        self.lb_widgets["time"] = wx.ListBox(self, wx.ID_ANY, size=(60,100), style=wx.LB_MULTIPLE)
        self.time_sizer.Add(self.time_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.time_sizer.Add(self.lb_widgets["time"], 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.time_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.multiple["time"] = True
        self.ch_sizer = wx.BoxSizer(wx.VERTICAL)
        self.ch_label = wx.StaticText(self, wx.ID_ANY, "ch. # | cold res. | warm .res")
        self.lb_widgets["ch"] = wx.ListBox(self, wx.ID_ANY, size=(120,100), style=wx.LB_MULTIPLE)
        self.ch_sizer.Add(self.ch_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.ch_sizer.Add(self.lb_widgets["ch"], 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.ch_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.multiple["ch"] = True
        self.mode_sizer = wx.BoxSizer(wx.VERTICAL)
        self.mode_label = wx.StaticText(self, wx.ID_ANY, "mode")
        self.lb_widgets["mode"] = wx.ListBox(self, wx.ID_ANY, size=(30,100), style=wx.LB_MULTIPLE)
        self.mode_sizer.Add(self.mode_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.mode_sizer.Add(self.lb_widgets["mode"], 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.mode_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.multiple["mode"] = True
        self.ray_sizer = wx.BoxSizer(wx.VERTICAL)
        self.ray_label = wx.StaticText(self, wx.ID_ANY, "ray #")
        self.lb_widgets["ray"] = wx.ListBox(self, wx.ID_ANY, size=(30,100), style=wx.LB_MULTIPLE)
        self.ray_sizer.Add(self.ray_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.ray_sizer.Add(self.lb_widgets["ray"], 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.ray_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.multiple["ray"] = True
        self.y_group_sizer = wx.BoxSizer(wx.VERTICAL)
        self.y_group_label = wx.StaticText(self, wx.ID_ANY, "y group")
        self.lb_widgets["y_group"] = wx.ListBox(self, wx.ID_ANY, size=(120,100), style=wx.LB_SINGLE)
        self.y_group_sizer.Add(self.y_group_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.y_group_sizer.Add(self.lb_widgets["y_group"], 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.lb_widgets["y_group"].Bind(wx.EVT_LISTBOX, self.OnYGroupSelected)
        self.multiple["y_group"] = False
        self.controlgrid.Add(self.y_group_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.y_quant_sizer = wx.BoxSizer(wx.VERTICAL)
        self.y_quant_label = wx.StaticText(self, wx.ID_ANY, "y quantity")
        self.lb_widgets["y_quant"] = wx.ListBox(self, wx.ID_ANY, size=(120,100), style=wx.LB_MULTIPLE)
        self.y_quant_sizer.Add(self.y_quant_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.y_quant_sizer.Add(self.lb_widgets["y_quant"], 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.lb_widgets["y_quant"].Bind(wx.EVT_LISTBOX, self.OnYQuantSelected)
        self.multiple["y_quant"] = True
        self.controlgrid.Add(self.y_quant_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.x_group_sizer = wx.BoxSizer(wx.VERTICAL)
        self.x_group_label = wx.StaticText(self, wx.ID_ANY, "x group")
        self.lb_widgets["x_group"] = wx.ListBox(self, wx.ID_ANY, size=(120,100), style=wx.LB_SINGLE)
        self.x_group_sizer.Add(self.x_group_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.x_group_sizer.Add(self.lb_widgets["x_group"], 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.lb_widgets["x_group"].Bind(wx.EVT_LISTBOX, self.OnXGroupSelected)
        self.multiple["x_group"] = False
        self.controlgrid.Add(self.x_group_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.x_quant_sizer = wx.BoxSizer(wx.VERTICAL)
        self.x_quant_label = wx.StaticText(self, wx.ID_ANY, "x quantity")
        self.lb_widgets["x_quant"] = wx.ListBox(self, wx.ID_ANY, size=(120,100), style=wx.LB_SINGLE)
        self.x_quant_sizer.Add(self.x_quant_label, 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.x_quant_sizer.Add(self.lb_widgets["x_quant"], 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.ALL, 5)
        self.controlgrid.Add(self.x_quant_sizer, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.multiple["x_quant"] = False
        self.eq_aspect_ratio_cb = simple_label_cb(self, "Equal aspect ratio", False)
        self.figure_width_tc = simple_label_tc(self, "Figure width", 12.0, "real")
        self.figure_height_tc = simple_label_tc(self, "Figure height", 8.5, "real")
        self.AddPlotButton = wx.Button(self, wx.ID_ANY, 'Add plot')
        self.AddPlotButton.Bind(wx.EVT_BUTTON, self.OnPlot)
        self.ClearButton = wx.Button(self, wx.ID_ANY, 'Clear plots')
        self.Bind(wx.EVT_BUTTON, self.OnClear, self.ClearButton)
        self.controlgrid2.Add(self.eq_aspect_ratio_cb, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid2.Add(self.figure_width_tc, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid2.Add(self.figure_height_tc, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid2.Add(self.AddPlotButton, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlgrid2.Add(self.ClearButton, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)
        self.controlplotsizer.Add(self.controlgrid, 0, \
                                    wx.LEFT | wx.ALL , 10)
        self.controlplotsizer.Add(self.controlgrid2, 0, \
                                    wx.LEFT | wx.ALL , 10)
        self.diag_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.controlplotsizer.Add(self.FigureControlPanel, 1, wx.ALL | wx.EXPAND, 10)
        self.diag_box_sizer = wx.BoxSizer(wx.VERTICAL)
        self.load_other_results_button = wx.Button(self, wx.ID_ANY, "Load other results")
        self.load_other_results_button.Bind(wx.EVT_BUTTON, self.OnLoadOtherResults)
        self.diag_box_sizer.Add(self.load_other_results_button, 0, wx.ALL | wx.EXPAND, 5)
        self.other_result_text = wx.StaticText(self, wx.ID_ANY, "Select result(s) for comparison")
        self.diag_box_sizer.Add(self.other_result_text, 0, wx.ALL | wx.TOP, 5)
        self.other_result_box = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE, size=(100,200))
        self.diag_box_sizer.Add(self.other_result_box, 0, wx.ALL | wx.EXPAND, 5)
        self.clear_other_results_button = wx.Button(self, wx.ID_ANY, "Clear other results")
        self.clear_other_results_button.Bind(wx.EVT_BUTTON, self.OnClearOtherResults)
        self.diag_box_sizer.Add(self.clear_other_results_button, 0, wx.ALL | wx.EXPAND, 5)
        self.diag_sizer.Add(self.diag_box_sizer, 0, wx.ALL | wx.LEFT, 10)
        self.sizer.Add(self.controlplotsizer, 1, wx.ALL | wx.EXPAND, 10)
        self.sizer.Add(self.diag_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        self.FigureControlPanel.Show(True)
        self.cur_selected_index = 0
        self.compare_data = {}
        

    def OnClearOtherResults(self, evt):
        self.other_result_box.Clear()
        self.compare_data = {}
        self.load_other_results_button.Enable()

    def OnYGroupSelected(self, evt):
        self.y_key = self.lb_widgets["y_group"].GetStringSelection()
        self.lb_widgets["mode"].Clear()
        if(self.y_key != "weights"):
            if("N_mode" in self.Results.shapes[self.y_key] or "N_mode_mix" in self.Results.shapes[self.y_key]):
                if(self.Results.Config["Physics"]["considered_modes"] == 1):
                    self.lb_widgets["mode"].Append("X")
                elif(self.Results.Config["Physics"]["considered_modes"] == 2):
                    self.lb_widgets["mode"].Append("O")
                else:
                    if("N_mode" in self.Results.shapes[self.y_key]):
                        self.lb_widgets["mode"].AppendItems(["X", "O"])
                    else:
                        self.lb_widgets["mode"].AppendItems(["Mix","X", "O"])
            self.lb_widgets["mode"].Select(0)
        self.lb_widgets["y_quant"].Clear()
        for sub_key in self.Results.sub_keys[self.y_key]:
            if(sub_key not in self.Results.failed_keys[self.y_key]):
                self.lb_widgets["y_quant"].Append(sub_key)
        self.lb_widgets["x_group"].Clear()
        self.lb_widgets["x_group"].AppendItems(self.Results.xaxis_link[self.y_key])
        self.lb_widgets["x_group"].Select(0)
        self.OnXGroupSelected(None)
    
    def OnYQuantSelected(self, evt):
        selection_list = self.lb_widgets["y_quant"].GetSelections()
        primary_unit, secondary_unit, bad_n_list = self.resolve_units(selection_list)
        for n in bad_n_list: 
            print("Can only plot two unique units at a time")
            self.lb_widgets["y_quant"].Deselect(n)                 
    
    def resolve_units(self, selection_list):
        primary_unit = None 
        secondary_unit = None
        bad_n_list = []
        for n in selection_list:
            if(primary_unit is None):
                primary_unit = self.Results.units[self.y_key][self.lb_widgets["y_quant"].GetString(n)]
                continue
            if(primary_unit != self.Results.units[self.y_key][self.lb_widgets["y_quant"].GetString(n)]):
                if(secondary_unit is None):
                    secondary_unit = self.Results.units[self.y_key][self.lb_widgets["y_quant"].GetString(n)]
                    continue
                elif(secondary_unit != self.Results.units[self.y_key][self.lb_widgets["y_quant"].GetString(n)]):
                    bad_n_list.append(n)
        return primary_unit, secondary_unit, bad_n_list

    def OnXGroupSelected(self, evt):
        select_group = self.lb_widgets["x_group"].GetStringSelection()
        self.lb_widgets["x_quant"].Clear()
        self.lb_widgets["x_quant"].Append("None")
        for sub_key in self.Results.sub_keys[select_group]:
            if(sub_key not in self.Results.failed_keys[select_group]):
                self.lb_widgets["x_quant"].Append(sub_key)
    

#         plot_type = self.plot_choice.GetStringSelection()
#         self.other_result_box.Clear()
#         if(plot_type in  self.compare_data):        
#             other_results = self.compare_data[plot_type]
#         elif(plot_type=="Ray" and "RayXRz" in self.compare_data):
#             other_results = self.compare_data["RayXRz"]
#         else:
#             return
#         other_results.sort()
#         self.other_result_box.AppendItems(other_results)
#         self.other_result_box.Layout()

    def OnUpdate(self, evt):
        self.Results = evt.Results
        if(len(self.Results.Scenario["time"]) > 0):
            for lb in self.lb_widgets.keys():
                self.lb_widgets[lb].Clear()
            self.lb_widgets["time"].AppendItems(self.Results.Scenario["time"].astype("|U7"))
            self.lb_widgets["time"].Select(0)
            for ich in range(self.Results["dimensions"]["N_ch"]):
                if(self.Results.Scenario["plasma"]["eq_dim"] == 3):
                    cold_res_key = "rhot_cold"
                    warm_res_key = "rhot_warm"
                else:
                    cold_res_key = "rhop_cold"
                    warm_res_key = "rhop_warm"
                self.lb_widgets["ch"].Append("{0:d} | {1:1.2f} | {2:1.2f}".format(ich + 1, \
                                                                                   self.Results["resonance"][cold_res_key][0][0][ich], \
                                                                                   self.Results["resonance"][warm_res_key][0][0][ich]))
            self.lb_widgets["ch"].Select(0)
            self.lb_widgets["ray"].AppendItems(np.array(range(1,self.Results["dimensions"]["N_ray"] + 1),dtype="|U7"))
            self.lb_widgets["ray"].Select(0)
            for key in self.Results.result_keys:
                if(key != "dimensions"):
                    self.lb_widgets["y_group"].Append(key)
            if(globalsettings.AUG):
                self.load_diag_data_button.Enable()
                self.OnClearDiags(None)
            self.load_other_results_button.Enable()  
                  

    def OnClearDiags(self, evt):
        self.diag_data = {}
        self.diag_box.Clear()
        

    def resolve_selection(self, compressed_selection):
        # Need to resolve the selection in the list boxes
        # into a list of indicies
        indices = []
        ndim = len(compressed_selection)
        multi_index = list((0,) * ndim)
        max_dim = ()
        for sub_sel in compressed_selection:
            max_dim += (len(sub_sel),)
        while True:
            indices.append(())
            for i_dim in range(ndim):
                # This loop only handles the inner most index 
                indices[-1] += (compressed_selection[i_dim][multi_index[i_dim]],)
            if(multi_index[ndim - 1] + 1 < max_dim[ndim - 1]):
                multi_index[ndim - 1] += 1
            else:
                found_new_index, multi_index = self.increment_outer_index(multi_index, ndim, max_dim)
                if(not found_new_index):
                    return indices
                    
    def increment_outer_index(self, multi_index, ndim, max_dim):
        cur_working_dim_index = ndim - 1
        while(cur_working_dim_index > 0):
            multi_index[cur_working_dim_index] = 0
            cur_working_dim_index -= 1
            if(multi_index[cur_working_dim_index] + 1 < max_dim[cur_working_dim_index]):
                multi_index[cur_working_dim_index] += 1            
                return True, multi_index
        return False, multi_index
            
    def OnPlot(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Plotting - please wait!')
        wx.PostEvent(self, evt)
        selections = {}
        for key in self.lb_widgets:
            if(self.multiple[key]):
                selections[key] = self.lb_widgets[key].GetSelections()
            else:
                selections[key] = self.lb_widgets[key].GetStringSelection()
            if(len(selections[key]) == 0):
                print("Please select a " + key.replace("_"," ").replace("quant","quantity"))
                return
        primary_unit, secondary_unit, _ = self.resolve_units(selections["y_quant"])
        x_list = []
        y_list = [[],[]] # main y axis/ second y axis
        label_list = [[],[]]
        x_axis_label = None
        y_axis_labels = ["",""]
        marker_type_list = [[],[]]
        for n_selected in selections["y_quant"]:
            sub_key = self.lb_widgets["y_quant"].GetString(n_selected)
            if(self.y_key != "weights"):
                shape_key = self.y_key
            else:
                shape_key = sub_key
            compact_index = ()
            index_labels = []
            # Get all the requested indices but through out the dimension used in the plot
            for shape_ref in self.Results.shapes[shape_key][:-1]:
                index_entry = []
                shape_ref_formatted = shape_ref.split("_")[1]
                for n in selections[shape_ref_formatted]:
                    index_entry.append(n)
                index_labels.append(shape_ref_formatted)
                compact_index += (index_entry,)
            # We need to express all the indices as an explicit tuple, i.e.
            # ([1,2], [0], [0], [3]) -> (1,0,0,3), (2,0,0,3)
            resolved_index_list = self.resolve_selection(compact_index)
            if(len(resolved_index_list) > 15):
                print("Sorry you can plot no more than 15 things at once.")
                print("Please deselect some of the fields to reduce the amount of plots.")
                print("If you have a use case that warrants more than 15 plots, please contact the developer.")
                return          
            if(self.Results.units[self.y_key][sub_key] == primary_unit):
                i_axis = 0
            else:
                i_axis = 1
            for index in resolved_index_list:
                if(x_axis_label is None):
                    if(selections["x_quant"] != "None"):
                        x_axis_label = self.Results.legend_entries[selections["x_group"]][selections["x_quant"]] + \
                                      self.Results.units[selections["x_group"]][selections["x_quant"]]
                    else:
                        x_axis_label = ""
                y_list[i_axis].append(self.Results[self.y_key][sub_key][index] * \
                                      self.Results.scales[self.y_key][sub_key])
                if(selections["x_quant"] != "None"):
                    x_list.append(self.Results[selections["x_group"]][selections["x_quant"]][index] * \
                                          self.Results.scales[selections["x_group"]][selections["x_quant"]])
                else:
                    if(self.Results.graph_style[self.y_key] == "line"):
                        x_list.append(np.linspace(0, 1, len(y_list[i_axis][-1])))
                    else:
                        x_list.append(np.linspace(1, len(y_list[i_axis][-1]), len(y_list[i_axis][-1])))
                label_list[i_axis].append(self.Results.legend_entries[self.y_key][sub_key])
                for ndim, _ in enumerate(index):
                    next_label = self.Results.get_index_reference(self.y_key, sub_key, ndim, index)
                    if(len(next_label) > 0):
                        label_list[i_axis][-1] += " " + next_label
                marker_type_list[i_axis].append(self.Results.graph_style[self.y_key])
                for comp_result in self.compare_data:
                    try:
                        y_list[i_axis].append(comp_result[self.y_key][sub_key][index] * \
                                              comp_result.scales[self.y_key][sub_key])
                        if(selections["x_quant"] != "None"):
                            x_list.append(comp_result[selections["x_group"]][selections["x_quant"]][index] * \
                                                  comp_result.scales[selections["x_group"]][selections["x_quant"]])
                        else:
                            if(comp_result.graph_style[self.y_key] == "line"):
                                x_list.append(np.linspace(0, 1, len(y_list[i_axis][-1])))
                            else:
                                x_list.append(np.linspace(1, len(y_list[i_axis][-1]), len(y_list[i_axis][-1])))
                        label_list[i_axis].append("{0:d} {1:d}: ".format(comp_result.Scenario["shot"], \
                                                                         comp_result.edition))
                        label_list[i_axis][-1] += comp_result.legend_entries[self.y_key][sub_key]
                        for ndim, _ in enumerate(index):
                            next_label = comp_result.get_index_reference(self.y_key, sub_key, ndim, index)
                            if(len(next_label) > 0):
                                label_list[i_axis][-1] += " " + next_label
                        marker_type_list[i_axis].append(comp_result.graph_style[self.y_key])
                    except Exception as e:
                        print("ERROR: Failed to add result comparison for: ")
                        print("ERROR: {0:d} {1:d}".format(comp_result.Scenario["shot"], \
                                                                       comp_result.edition))
                        print("INFO: The error is: " + str(e))
                        
            if(y_axis_labels[i_axis] == ""):                
                y_axis_labels[i_axis] = self.Results.labels[self.y_key][sub_key]
            else:
                if(self.Results.labels[self.y_key][sub_key] not in y_axis_labels[i_axis].split("/")):
                    y_axis_labels[i_axis] += "/" + self.Results.labels[self.y_key][sub_key]
        y_axis_labels[0] += " " + primary_unit
        if(secondary_unit is not None):
            y_axis_labels[1] += " " + secondary_unit
        eq_aspect_ratio = self.eq_aspect_ratio_cb.GetValue()
        figure_width = self.figure_width_tc.GetValue()
        figure_height = self.figure_height_tc.GetValue()
        self.FigureControlPanel.AddPlot(x_list, y_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
                                        eq_aspect_ratio, figure_width, figure_height)
        self.Layout()

    def OnClear(self, evt):
        self.FigureControlPanel.ClearFigureBook()

    
    def OnDiagDataLoaded(self, evt):
        for key in evt.DiagData:
            self.diag_data[key] = evt.DiagData[key]
        self.diag_box.Clear() 
        self.diag_box.AppendItems(list(self.diag_data))
        self.load_diag_data_button.Enable()
    
    def OnLoadOtherResults(self, evt):
        evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
        evt.SetStatus('Loading data - GUI might be unresponsive for a minute - please wait!')
        self.GetEventHandler().ProcessEvent(evt)
        plot_type = self.plot_choice.GetStringSelection()
        if(plot_type not in ["Trad", "Ray"]):
            print("Sorry only Trad and Ray supported at the moment")
            return
        if(self.Results is None):
            print("First load results before you compare")
            return
        dlg = wx.FileDialog(\
            self, message="Choose a preexisting calculation(s)", \
            defaultDir=self.Results.Config["Execution"]["working_dir"], \
            wildcard=('Matlab files (*.mat)|*.mat'),
            style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if(dlg.ShowModal() == wx.ID_OK):
            paths = dlg.GetPaths()
            dlg.Destroy()
            if(len(paths) > 0):
                WorkerThread(self.get_other_results, [paths, plot_type])
                self.load_other_results_button.Disable()
        
    def get_other_results(self, args):
        paths = args[0]
        new_results = {}
        for path in paths:
            result = ECRadResults()
            try:
                result.load(path)
                new_results[str(result.Scenario["shot"]) + "_" + str(result.edition)] = result
            except:
                print("Failed to load result at: " + path)
        evt_out = GenerticEvt(Unbound_EVT_OTHER_RESULTS_LOADED, self.GetId())
        evt_out.insertData(new_results)
        wx.PostEvent(self, evt_out)

    def OnOtherResultsLoaded(self, evt):
        for key in evt.Data:
            if(key not in self.compare_data):
                self.compare_data[key] = evt.Data[key]
            for entry in evt.Data[key]:
                self.compare_data[key][entry] = evt.Data[key][entry]
        resultlist = list(self.compare_data.keys())
        resultlist.sort()
        self.other_result_box.AppendItems(resultlist)
        self.load_other_results_button.Enable()

class FigureBook(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, wx.ID_ANY)
        self.FigureList = []

    def AddPlot(self, x_list, y_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
                eq_aspect_ratio, figure_width, figure_height):
        self.FigureList.append(PlotContainer(self, figure_width, figure_height))
        if(self.FigureList[-1].Plot(x_list, y_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
                                        eq_aspect_ratio)):
            self.AddPage(self.FigureList[-1], label_list[0][0])
        else:
            del(self.FigureList[-1])
            return
        if(not self.IsShown()):
            self.Show(True)
        return 0

    def ClearFigureBook(self):
        while self.GetPageCount() > 0:
            self.RemovePage(0)


class PlotContainer(wx.Panel):
    def __init__(self, parent, figure_width = 12.0, figure_height = 8.5):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.fig = plt.figure(figsize=(figure_width, figure_height), tight_layout=True, frameon=False)
        self.fig.clf()
        self.linestyles = ["-", "--", ":", "-."]
        self.markers = ["^", "v", "+", "d", "o"]
        self.cmap = plt.cm.ScalarMappable(plt.Normalize(0, 1), "rainbow")
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.axlist = []
        self.canvas.mpl_connect('motion_notify_event', self.UpdateCoords)
        self.Bind(EVT_DONE_PLOTTING, self.OnDonePlotting)
        self.plot_toolbar = NavigationToolbar2Wx(self.canvas)
        fw, th = self.plot_toolbar.GetSize().Get()
        self.plot_toolbar.SetSize(wx.Size(fw, th))
        self.plot_toolbar.Realize()
        self.ctrl_sizer.Add(self.plot_toolbar, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL , 5)
        self.lower_lim_tc = simple_label_tc(self, "lower limit", 0.0, "real")
        self.upper_lim_tc = simple_label_tc(self, "upper limit", 0.0, "real")
        self.axis_choice = wx.Choice(self, wx.ID_ANY)
        self.axis_choice.Append("x")
        self.axis_choice.Append("y1")
        self.axis_choice.Append("y2")
        self.axis_choice.Select(0)
        self.set_lim_button = wx.Button(self, wx.ID_ANY, "Set axis limits")
        self.set_lim_button.Bind(wx.EVT_BUTTON, self.OnSetLim)
        self.auto_lim_button = wx.Button(self, wx.ID_ANY, "Auto limits")
        self.auto_lim_button.Bind(wx.EVT_BUTTON, self.OnAutoLim)
        self.ctrl_sizer.Add(self.lower_lim_tc, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL , 5)
        self.ctrl_sizer.Add(self.upper_lim_tc, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL , 5)
        self.ctrl_sizer.Add(self.axis_choice, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL , 5)
        self.ctrl_sizer.Add(self.set_lim_button, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL , 5)
        self.ctrl_sizer.Add(self.auto_lim_button, 0, wx.ALL | \
                wx.ALIGN_CENTER_VERTICAL , 5)
        self.sizer.Add(self.ctrl_sizer, 0, wx.ALL | wx.LEFT , 5)
        self.sizer.Add(self.canvas, 0, wx.ALL | \
                       wx.LEFT, 5)
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
        # self.sizer.Add(self.fig_H_sizer, 0, wx.ALL | wx.EXPAND , 5)

    def OnSetLim(self, evt):
        try:
            lower = self.lower_lim_tc.GetValue()
            upper = self.upper_lim_tc.GetValue()
            if(self.axis_choice.GetSelection() == 0):
                self.axlist[0].set_xlim(lower,upper)
                self.canvas.draw_idle()
            elif(self.axis_choice.GetSelection() == 1):
                self.axlist[0].set_ylim(lower,upper)
                self.canvas.draw_idle()
            else:
                if(len(self.axislist) > 1):
                    self.axlist[1].set_ylim(lower,upper)
                    self.canvas.draw_idle()
        except Exception as e:
            print("Failed to set limits")
            print(e)
            
    def OnAutoLim(self, evt):
        try:
            if(self.axis_choice.GetSelection() == 0):
                self.pc_obj.axlist[0].set_xlim(auto=True)
                self.fig = self.pc_obj.fig
                self.canvas.draw_idle()
            elif(self.axis_choice.GetSelection() == 1):
                self.pc_obj.axlist[0].set_ylim(auto=True)
                self.fig = self.pc_obj.fig
                self.canvas.draw_idle()
            else:
                if(len(self.axislist) > 1):
                    self.axlist[1].set_ylim(auto=True)
                    self.canvas.draw_idle()
        except Exception as e:
            print("Failed to set limits")
            print(e)        
            
    def Plot(self, x_list, y_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
             eq_aspect_ratio):
        WorkerThread(self.plot_threaded, [x_list, y_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
             eq_aspect_ratio])
        return True

    def plot_threaded(self, args):
        x_list, y_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
             eq_aspect_ratio, = args
        # Does all the plotting in a separate step
        self.axlist.append(self.fig.add_subplot(111))
        n_ax = 1
        n_colors = len(y_list[0])
        if(len(y_axis_labels[1]) > 0):
            n_ax = 2
            self.axlist.append(self.axlist[0].twinx())
            n_colors += len(y_list[1])
        i_marker = 0
        i_line = 0
        icolor = 0
        color_list = self.cmap.to_rgba(np.linspace(0.0, 1.0, n_colors))
        for i_ax in range(n_ax):
            for x, y, label, marker in zip(x_list, y_list[i_ax], label_list[i_ax], marker_type_list[i_ax]):
                if(marker == "point"):
                    self.axlist[i_ax].plot(x, y, label=label, color=color_list[icolor], \
                                           linestyle="none", marker=self.markers[i_marker])
                    if(i_marker + 1 < len(self.markers)):
                        i_marker += 1
                    else:
                        i_marker = 0
                        
                else:
                    self.axlist[i_ax].plot(x, y, label=label, color=color_list[icolor], \
                                           linestyle=self.linestyles[i_line])
                    if(i_line + 1 < len(self.linestyles)):
                        i_line += 1
                    else:
                        i_line = 0
                icolor += 1
            self.axlist[i_ax].set_ylabel(y_axis_labels[i_ax])
            if(eq_aspect_ratio):
                self.axlist[i_ax].set_aspect("equal")
        if(n_ax > 1 or len(label_list[0]) > 1):
            lns = self.axlist[0].get_lines() 
            if(n_ax > 1):
                lns += self.axlist[1].get_lines() 
            labs = [l.get_label() for l in lns]
            leg = self.axlist[0].legend(lns, labs)
            leg.get_frame().set_alpha(0.5)
            leg.set_draggable(True)
        self.axlist[0].set_xlabel(x_axis_label)
        evt = UpdatePlotEvent(Unbound_EVT_DONE_PLOTTING, self.GetId())
#         evt.set_shot_time(args[0], args[1])
        wx.PostEvent(self, evt)
        
    def OnDonePlotting(self, evt):
#         self.fig.get_axes()[0].text(0.05, 1.02,  r" \# {0:d}, $t = $ {1:1.3f} s".format(evt.shot, evt.time),\
#                                     transform=self.fig.get_axes()[0].transAxes)
        self.canvas.draw()
        evt = wx.PyCommandEvent(Unbound_EVT_RESIZE, self.GetId())
        wx.PostEvent(self, evt)
        wx.PostEvent(self.Parent.Parent, evt) # There should be a way to avoid using Parent.Parent
        

    def UpdateCoords(self, event):
        if event.inaxes:
            evt = NewStatusEvt(Unbound_EVT_NEW_STATUS, self.GetId())
            x, y = event.xdata, event.ydata
            evt.SetStatus('x = {0:1.3e}: y = {1:1.3e}'.format(x, y))
            self.GetEventHandler().ProcessEvent(evt)
            
            