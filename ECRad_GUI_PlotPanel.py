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
        self.controlplotsizer.Add(self.FigureControlPanel, 1, wx.ALL | wx.EXPAND, 10)
        self.aux_data_box_sizer = wx.BoxSizer(wx.VERTICAL)
        self.load_other_results_button = wx.Button(self, wx.ID_ANY, "Load other results")
        self.load_other_results_button.Bind(wx.EVT_BUTTON, self.OnLoadOtherResults)
        self.aux_data_box_sizer.Add(self.load_other_results_button, 0, wx.ALL | wx.EXPAND, 5)
        self.other_result_text = wx.StaticText(self, wx.ID_ANY, "Select result(s) for comparison")
        self.aux_data_box_sizer.Add(self.other_result_text, 0, wx.ALL | wx.TOP, 5)
        self.other_result_box = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE, size=(100,200))
        self.aux_data_box_sizer.Add(self.other_result_box, 0, wx.ALL | wx.EXPAND, 5)
        self.clear_other_results_button = wx.Button(self, wx.ID_ANY, "Clear other results")
        self.clear_other_results_button.Bind(wx.EVT_BUTTON, self.OnClearOtherResults)
        self.aux_data_box_sizer.Add(self.clear_other_results_button, 0, wx.ALL | wx.EXPAND, 5)
        self.scenario_quant_text = wx.StaticText(self, wx.ID_ANY, "Add scenario quantity to plot")
        self.aux_data_box_sizer.Add(self.scenario_quant_text, 0, wx.ALL | wx.TOP, 5)
        self.scenario_quant_box = wx.ListBox(self, wx.ID_ANY, style=wx.LB_MULTIPLE, size=(100,200))
        self.aux_data_box_sizer.Add(self.scenario_quant_box, 0, wx.ALL | wx.EXPAND, 5)
        self.scenario_quant_box.Bind(wx.EVT_LISTBOX, self.OnScenarioQuantSelected)
        self.sizer.Add(self.controlplotsizer, 1, wx.ALL | wx.EXPAND, 10)
        self.sizer.Add(self.aux_data_box_sizer, 0, wx.ALL | wx.TOP, 10)
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
        if(self.y_key == "weights"):
            self.lb_widgets["mode"].Clear()
            for n in selection_list:
                sub_key = self.lb_widgets["y_quant"].GetString(n)
                if("N_mode" in self.Results.shapes[sub_key] or "N_mode_mix" in self.Results.shapes[sub_key]):
                    if(self.Results.Config["Physics"]["considered_modes"] == 1):
                        self.lb_widgets["mode"].Append("X")
                        break 
                    elif(self.Results.Config["Physics"]["considered_modes"] == 2):
                        self.lb_widgets["mode"].Append("O")
                        break 
                    else:
                        if("N_mode" in self.Results.shapes[sub_key]):
                            self.lb_widgets["mode"].AppendItems(["X", "O"])
                            break 
                        else:
                            self.lb_widgets["mode"].AppendItems(["Mix","X", "O"])
                            break 
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

    def OnScenarioQuantSelected(self, evt):
        selected_indices = self.scenario_quant_box.GetSelections()
        if(len(selected_indices) > 1): 
            for n in selected_indices:
                if(self.scenario_quant_box.GetString(n) not in ["Te", "ne"]):
                    print("Only Te and ne can be plotted simulateneously selected from the Scenario")
                    self.scenario_quant_box.Deselect(n)

    def OnUpdate(self, evt):
        self.Results = evt.Results
        for lb in self.lb_widgets.keys():
            self.lb_widgets[lb].Clear()
        self.scenario_quant_box.Clear()
        if(len(self.Results.Scenario["time"]) > 0):
            
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
            self.load_other_results_button.Enable()
            self.scenario_quant_box.AppendItems(["Te", "ne", "rhop", "Br", "Bt", "Bz"])  

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
            if(key in ["y_group", "y_quant", "x_group", "x_quant"]):
                if(len(selections[key]) == 0):
                    print("Please select a value for " + key.replace("_"," "))
                    return
        primary_unit, secondary_unit, _ = self.resolve_units(selections["y_quant"])
        scenario_selection = [] 
        for n_selected in self.scenario_quant_box.GetSelections():
            scenario_selection.append(self.scenario_quant_box.GetString(n_selected))
        if(len(scenario_selection) > 0):
            add_scenario_data = True
        else:
            add_scenario_data = False
        if(len(scenario_selection) > 1):
            if(primary_unit != "[keV]" or secondary_unit is not None):
                print("WARNING: No room for Te/ne -- skipping")
                add_scenario_data = False
        for scenario_select in scenario_selection:
            if(secondary_unit is not None):
                if(scenario_select == "Te"):
                    if("[keV]" not in [primary_unit, secondary_unit]):
                        print("WARNING: No room to plot Te -- skipping")
                        add_scenario_data = False
        x_list = []
        y_list = [] # main y axis/ second y axis
        z_list = [] # For contours
        # Whether primary or secondary axis
        axis_ref_list = []
        label_list = []
        x_axis_label = None
        y_axis_labels = [""]
        marker_type_list = []
        first_iter = True
        added_scenario_data = False
        for n_selected in selections["y_quant"]:
            sub_key = self.lb_widgets["y_quant"].GetString(n_selected)
            compact_index = ()
            index_labels = []
            if(self.y_key != "weights"):
                shape_key = self.y_key
            else:
                shape_key = sub_key   
            # Get all the requested indices but through out the dimension used in the plot
            for shape_ref in self.Results.shapes[shape_key][:-1]:
                index_entry = []
                shape_ref_formatted = shape_ref.split("_")[1]
                if(len(selections[shape_ref_formatted]) == 0):
                    print("Please select a value for " + shape_ref_formatted)
                    return
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
                y_list.append(self.Results[self.y_key][sub_key][index] * \
                              self.Results.scales[self.y_key][sub_key])
                axis_ref_list.append(i_axis)
                z_list.append(None)
                if(selections["x_quant"] != "None"):
                    x_list.append(self.Results[selections["x_group"]][selections["x_quant"]][index] * \
                                          self.Results.scales[selections["x_group"]][selections["x_quant"]])
                else:
                    if(self.Results.graph_style[self.y_key] == "line"):
                        x_list.append(np.linspace(0, 1, len(y_list[-1])))
                    else:
                        x_list.append(np.linspace(1, len(y_list[-1]), len(y_list[-1])))
                label_list.append(self.Results.legend_entries[self.y_key][sub_key])
                for ndim, _ in enumerate(index):
                    next_label = self.Results.get_index_reference(self.y_key, sub_key, ndim, index)
                    if(len(next_label) > 0):
                        label_list[-1] += " " + next_label
                marker_type_list.append(self.Results.graph_style[self.y_key])
                for n_result in self.other_result_box.GetSelections():
                    comp_result = self.compare_data[self.other_result_box.GetString(n_result)]
                    try:
                        y_list.append(comp_result[self.y_key][sub_key][index] * \
                                              comp_result.scales[self.y_key][sub_key])
                        axis_ref_list.append(i_axis)
                        z_list.append(None)
                        if(selections["x_quant"] != "None"):
                            x_list.append(comp_result[selections["x_group"]][selections["x_quant"]][index] * \
                                          comp_result.scales[selections["x_group"]][selections["x_quant"]])
                        else:
                            if(comp_result.graph_style[self.y_key] == "line"):
                                x_list.append(np.linspace(0, 1, len(y_list[-1])))
                            else:
                                x_list.append(np.linspace(1, len(y_list[-1]), len(y_list[-1])))
                        label_list.append("{0:d} {1:d}: ".format(comp_result.Scenario["shot"], \
                                                                 comp_result.edition))
                        label_list[-1] += comp_result.legend_entries[self.y_key][sub_key]
                        for ndim, _ in enumerate(index):
                            next_label = comp_result.get_index_reference(self.y_key, sub_key, ndim, index)
                            if(len(next_label) > 0):
                                label_list[-1] += " " + next_label
                        marker_type_list.append(comp_result.graph_style[self.y_key])
                    except Exception as e:
                        print("ERROR: Failed to add result comparison for: ")
                        print("ERROR: {0:d} {1:d}".format(comp_result.Scenario["shot"], \
                                                                       comp_result.edition))
                        print("INFO: The error is: " + str(e))
            if(i_axis == 1 and len(y_axis_labels) == 1):
                y_axis_labels.append("")
            if(y_axis_labels[i_axis] == ""):                
                y_axis_labels[i_axis] = self.Results.labels[self.y_key][sub_key]
            else:
                if(self.Results.labels[self.y_key][sub_key] not in y_axis_labels[i_axis].split("/")):
                    y_axis_labels[i_axis] += "/" + self.Results.labels[self.y_key][sub_key]
            # Add additional scenario data for the plot
            if(add_scenario_data and not added_scenario_data):
                added_scenario_data = True
                if(scenario_selection[0] in ["Te","ne"] and not self.Results.Scenario["plasma"]["2D_prof"]):
                    if(not selections["x_quant"].startswith("rho")):
                        print("Cannot plot Te/ne if x_axis is not rhop/rhot")
                        add_scenario_data = False
                    elif(first_iter):
                        for scenario_select in scenario_selection:
                            for itime in selections["time"]:
                                if(selections["x_quant"].startswith("rhop")):
                                    if(len(self.Results.Scenario["plasma"]["rhop_prof"][itime]) > 0):
                                        x_list.append(self.Results.Scenario["plasma"]["rhop_prof"][itime] * \
                                                      self.Results.Scenario["scaling"][scenario_select + "_rhop_scale"])
                                elif(selections["x_quant"].startswith("rhot")):
                                    if(len(self.Results.Scenario["plasma"]["rhot_prof"][itime]) > 0):
                                        x_list.append(self.Results.Scenario["plasma"]["rhot_prof"][itime] * \
                                                      self.Results.Scenario["scaling"][scenario_select + "_rhop_scale"])
                                if(scenario_select == "Te"):
                                    if(primary_unit == "[keV]"):
                                        i_axis = 0
                                    else:
                                        i_axis = 1
                                    y_list.append(self.Results.Scenario["plasma"][scenario_select][itime] / 1.e3 * \
                                                        self.Results.Scenario["scaling"]["Te_scale"])
                                else:
                                    if(primary_unit == "[$\times 10^{19}$m$^{-3}$]"):
                                        i_axis = 0
                                    else:
                                        i_axis = 1
                                    y_list.append(self.Results.Scenario["plasma"][scenario_select][itime] / 1.e19 * \
                                                        self.Results.Scenario["scaling"]["ne_scale"])  
                                label_list.append(self.Results.Scenario.labels[scenario_select] + r" $t =$ " + \
                                                  "{0:1.3f} s".format(self.Results.Scenario["time"][itime]))
                                axis_ref_list.append(i_axis)
                                marker_type_list.append("line")
                                if(len(y_axis_labels) == 1 and i_axis > 0):
                                    y_axis_labels.append("")
                                if(y_axis_labels[i_axis] == ""):                
                                    y_axis_labels[i_axis] = self.Results.Scenario.labels[scenario_select]
                                else:
                                    if(self.Results.Scenario.labels[scenario_select] not in y_axis_labels[i_axis].split("/")):
                                        y_axis_labels[i_axis] += "/" + self.Results.Scenario.labels[scenario_select]
                                if(secondary_unit is None and i_axis == 1):
                                    secondary_unit = " " + self.Results.Scenario.units[scenario_select]
                                z_list.append(None)
                elif((scenario_selection[0] in ["rhop", "Br", "Bt", "Bz"]) or \
                     (scenario_selection[0] in ["Te","ne"] and self.Results.Scenario["plasma"]["2D_prof"])):
                    if(selections["x_quant"] != "R" or sub_key != "z"):
                        print("Cannot plot " + scenario_selection[0] + "x-y axes have to be R, z")
                        add_scenario_data = False
                    elif(first_iter):
                        if(len(selections["time"]) > 1):
                            print("WARNING: Multiple time points selected, but contour plot only useful for single time point")
                            print("WARNING: Plotting smalles selected time point")
                        time = self.Results.Scenario["time"][selections["time"][0]]
                        eq_slice = self.Results.Scenario["plasma"]["eq_data_2D"].GetSlice(time, bt_vac_correction=self.Results.Scenario["plasma"]["Bt_vac_scale"])
                        x_list.append(eq_slice.R)
                        y_list.append(eq_slice.z)
                        if(scenario_selection[0] not in ["Te", "ne"]):
                            z_list.append(getattr(eq_slice, scenario_selection[0]))
                        else:
                            if(scenario_selection[0] == "Te"):
                                z_list.append(self.Results.Scenario["plasma"][scenario_selection[0]][selections["time"][0]] / 1.e3 * \
                                              self.Results.Scenario["scaling"]["Te_scale"])
                            else:
                                z_list.append(self.Results.Scenario["plasma"][scenario_selection[0]][selections["time"][0]] / 1.e19 * \
                                              self.Results.Scenario["scaling"]["ne_scale"])
                        label_list.append(self.Results.Scenario.labels[scenario_selection[0]] + " " + self.Results.Scenario.units[scenario_selection[0]])
                        axis_ref_list.append(0)
                        if(scenario_selection[0] == "rhop"):
                            marker_type_list.append("contour")
                        else:
                            marker_type_list.append("contourf")
        y_axis_labels[0] += " " + primary_unit
        if(secondary_unit is not None):
            y_axis_labels[1] += " " + secondary_unit
        eq_aspect_ratio = self.eq_aspect_ratio_cb.GetValue()
        figure_width = self.figure_width_tc.GetValue()
        figure_height = self.figure_height_tc.GetValue()
        self.FigureControlPanel.AddPlot(x_list, y_list, z_list, axis_ref_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
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
        if(self.Results is None):
            print("First load results before you compare")
            return
        dlg = wx.FileDialog(\
            self, message="Choose a preexisting calculation(s)", \
            defaultDir=self.Results.Config["Execution"]["working_dir"], \
            wildcard=("Matlab and Netcdf4 files (*.mat;*.nc)|*.mat;*.nc"),
            style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if(dlg.ShowModal() == wx.ID_OK):
            paths = dlg.GetPaths()
            dlg.Destroy()
            if(len(paths) > 0):
                WorkerThread(self.get_other_results, [paths])
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

    def AddPlot(self, x_list, y_list, z_list, axis_ref_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
                eq_aspect_ratio, figure_width, figure_height):
        self.FigureList.append(PlotContainer(self, figure_width, figure_height))
        if(self.FigureList[-1].Plot(x_list, y_list, z_list, axis_ref_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
                                        eq_aspect_ratio)):
            self.AddPage(self.FigureList[-1], label_list[0])
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
                if(len(self.axlist) > 1):
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
            
    def Plot(self, x_list, y_list, z_list, axis_ref_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
             eq_aspect_ratio):
        WorkerThread(self.plot_threaded, [x_list, y_list, z_list, axis_ref_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
             eq_aspect_ratio])
        return True

    def plot_threaded(self, args):
        x_list, y_list, z_list, axis_ref_list, label_list, marker_type_list, x_axis_label, y_axis_labels, \
             eq_aspect_ratio, = args
        # Does all the plotting in a separate step
        self.axlist.append(self.fig.add_subplot(111))
        n_ax = 1
        if(len(y_axis_labels) > 1):
            self.axlist.append(self.axlist[0].twinx())
            n_ax += 1
        n_colors = len(y_list) 
        i_marker = 0
        i_line = 0
        icolor = 0
        color_list = self.cmap.to_rgba(np.linspace(0.0, 1.0, n_colors))
        for x, y, z, i_ax, label, marker in zip(x_list, y_list, z_list, axis_ref_list, label_list, marker_type_list):
            if(marker == "point"):
                self.axlist[i_ax].plot(x, y, label=label, color=color_list[icolor], \
                                       linestyle="none", marker=self.markers[i_marker])
                if(i_marker + 1 < len(self.markers)):
                    i_marker += 1
                else:
                    i_marker = 0
            elif(marker == "line"):
                self.axlist[i_ax].plot(x, y, label=label, color=color_list[icolor], \
                                       linestyle=self.linestyles[i_line])
                if(i_line + 1 < len(self.linestyles)):
                    i_line += 1
                else:
                    i_line = 0
            elif(marker == "contourf"):
                cont = self.axlist[0].contourf(x, y, z.T, cmap=plt.get_cmap("plasma"))
                cbar = self.fig.colorbar(cont, ax=self.axlist[0])
                cbar.ax.set_ylabel(label)
            else:# contour of rhop
                cont = self.axlist[0].contour(x, y, z.T, levels=np.linspace(0.1, 1.2, 12), \
                                              linewidths=1, colors="k", linestyles="--")
            icolor += 1
        for i_ax, label in enumerate(y_axis_labels):
            self.axlist[i_ax].set_ylabel(label)
        if(eq_aspect_ratio):
            self.axlist[i_ax].set_aspect("equal")
        if(len(label_list) > 1):
            lns = self.axlist[0].get_lines()
            if(n_ax > 1):
                lns += self.axlist[1].get_lines() 
            labs = []
            lns_short = []
            for ln in lns:
                if(not ("_"  in ln.get_label() and "$" not in ln.get_label())):
                    labs.append(ln.get_label())
                    lns_short.append(ln)
            leg = self.axlist[0].legend(lns_short, labs)
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