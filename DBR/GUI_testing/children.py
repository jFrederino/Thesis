import dearpygui.dearpygui as dpg
import dearpygui_ext.logger as dpg_logger

dpg.create_context()


def dark_callback(sender, data):
    print("dark")
    try: logger.log("dark")
    except: pass
    
def open_logger(sender, data):
    global logger 
    logger = dpg_logger.mvLogger()
    logger.log("Welcome to the logger !")

with dpg.window(label="Main"):

    with dpg.menu_bar():
        with dpg.menu(label="Themes"):
            dpg.add_menu_item(label="Dark", callback=dark_callback)
            dpg.add_menu_item(label="Light")
            dpg.add_menu_item(label="Classic")

            with dpg.menu(label="Other Themes"):
                dpg.add_menu_item(label="Purple")
                dpg.add_menu_item(label="Gold")
                dpg.add_menu_item(label="Red")

        with dpg.menu(label="Tools"):
            dpg.add_menu_item(label="Show Logger", callback=open_logger)
            dpg.add_menu_item(label="Show About")

        with dpg.menu(label="Oddities"):
            dpg.add_button(label="A Button")
            dpg.add_simple_plot(label="Menu plot", default_value=(0.3, 0.9, 2.5, 8.9), height=80)

dpg.create_viewport(title='Custom Title', width=800, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()