from time import sleep

import includes.helpers as helpers
from blinker import signal
from rpilcdmenu import *
from rpilcdmenu.items import *

tools = helpers.tools()

class menu_manager:

    def __init__(self):
        self.set_mode = signal('set-mode')
        self.menu = RpiLCDMenu(7, 8, [25, 24, 23, 15])
        self.menu.message("Initialising")
        # Not sure why the below are neededs
        # self.menu.start()
        # self.menu.debug()

    def render_16x2(self, scrolling_text, index):
        try:
            lines = scrolling_text.split('\n')
            line1 = lines[0]
            line2 = lines[1]
            last_char = index + 15
            line1_vfd = "{:<16}".format(line1[index:last_char])
            line2_vfd = "{:<16}".format(line2[index:last_char])
            return ("%s\n%s" % (line1_vfd, line2_vfd))
        except Exception as e:
            return (e)

    def scroll_text(self, input_message):
        try:
            lines = input_message.split('\n')

            if len(lines) > 2:
                return self.menu.message('Too many lines'.upper())

            len1 = len(lines[0])
            len2 = len(lines[1])

            # add one to the longest length so it scrolls off screen
            if len1 < len2:
                text_length = len2 + 1
            else:
                text_length = len1 + 1

            # render the initial text for 3 seconds
            self.menu.clearDisplay()
            text = self.render_16x2(input_message, 0)
            self.menu.message(text.upper())
            sleep(3)

            # scroll the message right to left
            for index in range(1, text_length):
                self.menu.clearDisplay()
                text = self.render_16x2(input_message, index)
                self.menu.message(text.upper())
                sleep(0.05)

            # display the message again
            self.menu.clearDisplay()
            text = self.render_16x2(input_message, 0)
            self.menu.message(text.upper())

        except Exception as e:
            self.menu.message(e)

    def display_message(self, message, clear=False, static=False):
        # clear will clear the display and not render anything after
        # static will scroll the message then leave  on screen
        # the default will render the menu after 2 secondss
        if self.menu != None:
            self.menu.clearDisplay()
            if clear == True:
                self.menu.message(message.upper())
                sleep(2)
                self.menu.clearDisplay()
                return self.menu.clearDisplay()
            elif static == True:
                # return self.scroll_text(message)
                return self.menu.message(message.upper(), autoscroll=True)
            else:
                self.menu.message(message.upper())
                sleep(2)
                return self.menu.render()
        return

    def build_service_menu(self, services):

        # Clear menu if it's not empty as you cannot remove menu items
        if self.menu != None:
            self.menu = None
            self.menu = RpiLCDMenu(7, 8, [25, 24, 23, 15])

        menu_item = 1

        try:
            for i in services:
                for k, v in i.items():
                    name = v['name']
                    service = v['details']['service']
                    dependancies = v['details']['dependancies']
                    if self.check_service(service) == "0":
                        # FunctionItem(Menu Entry, function, function options)
                        menu_function = FunctionItem(("%s ON" % name).upper(), self.service_manager,
                                                     [menu_item, 'stop', name, services])
                        self.menu.append_item(menu_function)
                        menu_item = + 1
                    else:
                        menu_function = FunctionItem(("%s OFF" % name).upper(), self.service_manager,
                                                     [menu_item, 'start', name, services])
                        self.menu.append_item(menu_function)
                        menu_item = + 1

        except Exception as e:
            print(e)

        # return rendered menu
        # if you do not return the menu it will render the original one again
        return self.menu.render()

    def service_manager(self, item, action, name, service_list):

        # set  variables
        failed = []
        service = None

        # get the service name you wish to action
        for i in service_list:
            for k, v in i.items():
                n = v['name']
                s = v['details']['service']
                d = v['details']['dependancies']
                if n == name:
                    service = s

        # print("service is " + str(service))
        # stop all other services if you're starting another, then start the dependencies we need
        if action == 'start' and service != None or action == 'stop-all' and name == None:
            # read all service items except the one you're starting and stop them and their dependencies
            # or stop all services
            for i in service_list:
                for k, v in i.items():
                    n2 = v['name']
                    s2 = v['details']['service']
                    d2 = v['details']['dependancies']
                    if n2 == name:
                        pass
                    else:
                        status = str(tools.service(s2, 'stop'))
                        if status == "1":
                            failed.append(n2)
                        for i in d2:
                            # print(i)
                            d_service = d2[i]['service']
                            d_on_action = d2[i]['on_action']
                            d_action = d2[i]['action']
                            if d_on_action == 'stop':
                                d_status = str(tools.service(d_service, d_action))
                                if d_status == "1" and d_action != 'disable':
                                    failed.append(d_service)
                # start the service dependenices
            for i in service_list:
                for k, v in i.items():
                    n3 = v['name']
                    s3 = v['details']['service']
                    d3 = v['details']['dependancies']
                    if n3 == name:
                        for i in d3:
                            # print(i)
                            d_service = d3[i]['service']
                            d_on_action = d3[i]['on_action']
                            d_action = d3[i]['action']
                            if d_on_action == 'start':
                                d_status = str(tools.service(d_service, d_action))
                                if d_status == "1" and d_action != 'disable':
                                    failed.append(d_service)

        # show error message on failure
        if len(failed) > 0:
            for i in failed:
                self.display_message("Failed to stop or start\n%s" % i)

        elif service != None:
            # proceed with other action if theres no failures
            status = str(tools.service(service, action))
            # if starting the service is successful
            if status == "0" and action == 'start':
                self.set_mode.send('menu_manager', mode=name)
                self.display_message("%s\nenabled" % name)
            elif status == "0" and action == 'stop':
                self.set_mode.send('menu_manager', mode=None)
                self.display_message("%s\ndisabled" % name)
            elif status == "0":
                self.display_message("%s\nprocessed" % name)
            else:
                self.display_message("Failed to process\n%s " % name)

        # rebuild the menu so long as a menu exists
        if self.menu != None:
            return self.build_service_menu(service_list)
        return

    def check_service(self, service):
        status = str(tools.service(service, 'status'))
        return status
