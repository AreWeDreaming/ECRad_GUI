'''
Created on Feb 5, 2021

@author: denk
'''
def resolve_selection(compressed_selection):
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
                found_new_index, multi_index = increment_outer_index(multi_index, ndim, max_dim)
                if(not found_new_index):
                    return indices
                    
                
                
                 
def increment_outer_index(multi_index, ndim, max_dim):
    cur_working_dim_index = ndim - 1
    while(cur_working_dim_index > 0):
        multi_index[cur_working_dim_index] = 0
        cur_working_dim_index -= 1
        if(multi_index[cur_working_dim_index] + 1 < max_dim[cur_working_dim_index]):
            multi_index[cur_working_dim_index] += 1            
            return True, multi_index
    return False, multi_index

if(__name__ == "__main__"):
    print(resolve_selection(([2,3], [1,2], [2], [1,4,6])))
    