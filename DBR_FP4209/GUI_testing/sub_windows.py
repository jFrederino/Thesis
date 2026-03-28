# Source - https://stackoverflow.com/q/74610549
# Posted by Katwick
# Retrieved 2026-03-07, License - CC BY-SA 4.0

import dearpygui.dearpygui as dpg

item_table = []

#builts the context window
dpg.create_context()
dpg.create_viewport(title="invengo", width=600, height=600)

#outputs the data from the inputs and callbacks
def reg(sender):
    print(dpg.get_value(sender))
    item_table.append(dpg.get_value(sender))

def lel(sender):
    with dpg.window():
        pass
        
#builts the datainputs 
with dpg.window(tag="PW"):
    item_name = dpg.add_input_text(label="Gegenstand", hint="Hier den Namen des Gegenstandes eintragen...",callback=reg, on_enter=True)
    item_amount = dpg.add_combo(label="Menge", default_value=1, items=(1,2,3,"Mehrere"), callback=reg)
    check_button = dpg.add_button(label="CLICK ME", callback=lel)
dpg.set_item_callback(item_name, reg)

#debugging
print(dpg.get_value(item_name))

#start the modul  
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("PW", True)
dpg.start_dearpygui()
dpg.destroy_context()

#debugging
print(item_table)
