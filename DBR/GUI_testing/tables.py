import dearpygui.dearpygui as dpg

dpg.create_context()


current_highlighted_row_tag = None
table_tag = None


def get_table_row_id_by_row_tag(row_tag: int):
    row_tag_id = None
    row_tag_ids = dpg.get_item_children(table_tag)[1]
    print(row_tag_ids)
    for id in row_tag_ids:
        if id == row_tag:
            row_tag_id = id
            break

    if row_tag_id:
        return row_tag_ids.index(row_tag_id)

    return None


def on_mouse_left_button_clicked(sender, app_data, text_tag):
    global current_highlighted_row_tag
    clicked_row_tag = dpg.get_item_parent(text_tag)

    if not current_highlighted_row_tag:
        highlight_row(clicked_row_tag)

    elif current_highlighted_row_tag != clicked_row_tag:
        unhighlight_row(current_highlighted_row_tag)
        highlight_row(clicked_row_tag)


def highlight_row(row_tag):
    global current_highlighted_row_tag
    color_code = [35, 200, 83, 100]

    row_id = get_table_row_id_by_row_tag(row_tag)
    print("Highlighted: Row ", row_id)
    if row_id is not None:
        dpg.highlight_table_row(table_tag, row_id, color_code)
        current_highlighted_row_tag = row_tag


def unhighlight_row(row_tag):
    global current_highlighted_row_tag
    row_id = get_table_row_id_by_row_tag(row_tag)
    print("Unhighlighted: Row ", row_id)
    if row_id is not None:
        dpg.unhighlight_table_row(table_tag, row_id)
        current_highlighted_row_tag = None
    

with dpg.window(label="Tutorial"):
    table_tag = dpg.generate_uuid()
    with dpg.table(header_row=False, tag=table_tag, row_background=True,
                   borders_innerH=True, borders_outerH=True, borders_innerV=True,
                   borders_outerV=True):

        # use add_table_column to add columns to the table,
        # table columns use child slot 0
        dpg.add_table_column()
        dpg.add_table_column()
        dpg.add_table_column()

        # add_table_next_column will jump to the next row
        # once it reaches the end of the columns
        # table next column use slot 1
        for i in range(0, 4):
            with dpg.table_row():
                for j in range(0, 3):
                    text_tag = dpg.add_text(f"Row{i} Column{j}")

                    with dpg.item_handler_registry() as event:
                        dpg.add_item_clicked_handler(
                            0, callback=on_mouse_left_button_clicked, 
                            user_data=text_tag
                        )

                    dpg.bind_item_handler_registry(text_tag, event)

    # =====================================================
    # Reorder items 
    # The following codes can be removed to produce the working version 
    # before reorder_item is applied
    row_tags = dpg.get_item_children(table_tag)[1]
    print("Original table row tag order:", row_tags)
    reverse_ordered_row_tags = list(reversed(row_tags))
    print("Revered table row tag order:", reverse_ordered_row_tags)
    dpg.reorder_items(table_tag, 1, reverse_ordered_row_tags)
    # =====================================================


dpg.create_viewport(title='Custom Title', width=800, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()