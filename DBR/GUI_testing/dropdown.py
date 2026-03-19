import dearpygui.dearpygui as dpg



dpg.create_context()
dpg.create_viewport()

def get_item(sender, app_data, user_data):    
    cfg = dpg.get_item_configuration(sender)    
    for cnt, item in enumerate(cfg['items']):        
        if item == app_data:
                print(cnt+1)
                print(f"item {app_data} is on line {cnt+1}")

with dpg.window(label="Tutorial"):
    i_tems=['test1', 'test2', 'test3', 'test4']
    dpg.add_listbox(items=i_tems, callback=get_item)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()