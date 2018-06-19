import fdutils.selenium_util.locator_utils as loc


@loc.locator_or_string()
def select_preceded_by_label(label):
    return loc.label_before(label)("select")


_combo = "//div[contains(@role, 'combobox')]"
_combo_open = _combo[:-1]
_combo_opener = "/div[@class='v-filterselect-button' and @role='button']"


@loc.locator_or_string()
def tab_label(label):
    return "//div[contains(@class, 'v-tabsheet-tabitem')]//descendant-or-self::*//div[.='{label}']" \
           "".format(label=label)

vaadin_tab_item_selected_class = 'v-tabsheet-tabitem-selected'
@loc.locator_or_string()
def tab_label_with_focus(label):
    return "//div[contains(@class, 'v-tabsheet-tabitem') and contains(@class, 'v-tabsheet-tabitem-selected')]" \
           "//descendant-or-self::*//div[.='{label}']" \
           "".format(label=label)


@loc.locator_or_string()
def result_panel_preceded_by_label(label):
    return loc.label_before(label)("div[contains(@class, 'v-panel-content')]")


@loc.locator_or_string()
def tree_menu_node(node_name):
    """ for the vertical tree menus often used """
    return "//div[contains(@class, 'v-tree-node-caption') and .//span[.='{node}']]".format(node=node_name)


@loc.locator_or_string()
def menu_bar_tree_node(node_name):
    """ for the horizontal menu to select the main actions"""
    return "//div[contains(@class, 'v-menubar')]//span[contains(@class, 'v-menubar-menuitem-caption') " \
           "and .='{node_name}']".format(node_name=node_name)


@loc.locator_or_string()
def tree_menu_node_caption(node_name):
    return tree_menu_node(node_name, as_str=True) + "//span"


_tree_node_arrow_open = "//td//span[contains(@class, 'v-treetable-node-open')]"
_tree_node_arrow_close = "//td//span[contains(@class, 'v-treetable-node-closed')]"


@loc.locator_or_string()
def tree_table_node_child(node_name, child_name):
    return "(//div[contains(@class, 'v-label') and .='{child_name}' and ./ancestor::*/tr{node_locator}])[1]" \
           "".format(child_name=child_name, node_locator=tree_table_node(node_name, as_str=True))


@loc.locator_or_string(no_highlight=True)
def notification_error():
    return "//div[@role='alert' and contains(@class, 'v-Notification-error')]"


@loc.locator_or_string()
def button(button_label):
    return "//span[@class='v-button-wrap' and .='{text}']".format(text=button_label)


@loc.locator_or_string()
def button_locator_icon(icon_png):
    return "//span[@class='v-button-wrap']/img[@class='v-icon' and contains(@src, '{icon}')]".format(icon=icon_png)


@loc.locator_or_string()
def button_indexed(button_label):
    return "(//span[@class='v-button-caption' and .='{text}'])[{{}}]".format(text=button_label)


@loc.locator_or_string()
def button_icon_indexed(icon_png):
    return "(//span[@class='v-button-wrap']/img[@class='v-icon' and contains(@src, '{icon}')])[{{}}]" \
           "".format(icon=icon_png)


@loc.locator_or_string()
def file_input_followed_by_button(button_label):
    return button(button_label, as_str=True) + "/preceding::input[@type='file'][1]"


@loc.locator_or_string()
def tree_menu_child(node_name, child_name):
    # expecting only one level down
    return ("{node_loc}/following-sibling::div[contains(@class, 'v-tree-node-children')]//span[.='{child}']"
            "".format(node_loc=tree_menu_node(node_name, as_str=True), child=child_name))


@loc.locator_or_string()
def table_with_header_value(header_value):
    return "(//div[contains(@class, 'v-table-header') and .//div[contains(@class, 'v-table-caption-container') " \
           "and text()='{header_value}']]/ancestor::*//div[contains(@class, 'v-table')])[1]" \
           "".format(header_value=header_value)


@loc.locator_or_string()
def table_header_tds():
    return "//div[contains(@class, 'v-table-header')]/*//td"


@loc.locator_or_string()
def loading_indicator():
    return '//div[contains(@class,"v-loading-indicator")]'


@loc.locator_or_string()
def table_rows_tds():
    return "//div[contains(@class, 'v-table-body-wrapper')]/*//td"


@loc.locator_or_string()
def table_rows_input():
    return "//div[contains(@class, 'v-table-body-wrapper')]/*//input"


def table_info(label):
    return loc.locator("//div[.='{label}']/following-sibling::div[1]".format(label=label))


def notification_popup(label):
    return loc.locator("//div[contains(@class, 'v-Notification')]/"
                       "div[contains(@class, 'popupContent') and contains(., '{label}')]".format(label=label))


def combo_opener_followed_by_button_labeled(button_label):
    return loc.locator(_combo_open + " and ../following-sibling::*{button_loc}]{combo_opener}"
                                     "".format(button_loc=button(button_label, as_str=True),
                                               combo_opener=_combo_opener))


def combo_opener_followed_by_label(label):
    return loc.locator(loc.label_after(label)(_combo.lstrip('/')) + _combo_opener)


def combo_opener_preceded_by_label(label):
    return loc.locator(loc.label_before(label)(_combo.lstrip('/')) + _combo_opener)


def link_menu_preceded_by_label(label):
    return loc.locator("//div[.='{label}']/following-sibling::*//span[contains(@class,'v-menubar-menuitem-caption')]"
                       "".format(label=label))


@loc.locator_or_string()
def grid_locator_containing_label(label):
    return "//div[contains(@class, 'v-gridlayout') and .//div[contains(@class, 'v-gridlayout-slot') and .='{label}']]" \
           "".format(label=label)


@loc.locator_or_string()
def tree_table_node(node_name):
    return _tree_node_arrow_open + \
           "/following-sibling::*//div[contains(@class, 'v-label') and .='{node}']".format(node=node_name)


loc.add_str_to_raw_locators(__name__)

