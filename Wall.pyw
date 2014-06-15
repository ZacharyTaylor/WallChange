import wx

import urllib
from bs4 import BeautifulSoup
import re

from random import choice

import os
import sys
from ctypes import *
from os import path

import time
import shutil
import subprocess

class SetWallpaper:

    def __init__(self, wall_dir):

        self.wall_dir = wall_dir

        #blacklist to use in removing wallpapers
        self.black_list = BlackList(self.wall_dir)

    #True if wallpaer passes, false if a double up or on blacklist
    def check_wallpaper(self, wall):
        #check for blacklisted tags
        if self.black_list.check(wall['tags']):
            return False

        #check to see if wallpaper is new
        wall_num = wall['url'].split('/')[-1]
        os.chdir(self.wall_dir)
        for file in os.listdir("."):
            #needed to prevent non ascii characters throwing exception
            file = file.decode('ISO-8859-1')
            if wall_num in file:
                return False
        
        return True

    def set_next_wallpaper(self):

        wall_haven = WallHaven()

        #loop until wallpaper found
        while True:
            wall = wall_haven.get_next_wall_info()
            if self.check_wallpaper(wall):
                break


        #get wallpaper
        wall = wall_haven.get_wall(wall)
        wall['name'] = wall['name'].encode('ISO-8859-1', 'ignore')
        urllib.urlretrieve(wall['wallpaper'], self.wall_dir + wall['name'])

        #set wallpaper
        path = self.wall_dir + wall['name']

        SPI_SETDESKWALLPAPER = 0x14
        SPIF_UPDATEINIFILE   = 0x1

        SystemParametersInfo = windll.user32.SystemParametersInfoA

        SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE)




class WallHaven:
    def __init__(self):

        #links used by wallhaven
        self.walls = 'http://alpha.wallhaven.cc/wallpaper/search'
        self.wall_options = '?categories=100&purity=100&resolutions=1920x1080&sorting=random&order=desc'

        #index of current wallpaper
        self.wall_idx = 0
        self.walls_per_page = 20


    #grabs list of wallpaper urls and tags from wallhaven
    def refresh_wall_list(self):
        #get site
        url = urllib.urlopen(self.walls + self.wall_options).read()
        site = BeautifulSoup(url)

        #find wall info
        urls = site.findAll('a', {'href': re.compile('^http://alpha.wallhaven.cc/wallpaper/\d+')})
        tags = site.findAll('ul', {'class':'thumb-tags'})

        #format tags and url
        self.wall_tags = []
        self.wall_urls = []

        for i in range(0,self.walls_per_page):
           self.wall_urls.append(urls[i]['href'])
           self.wall_tags.append('')
           for names in tags[i]:
               if hasattr(names, 'text'):
                    self.wall_tags[-1] = self.wall_tags[-1] + ' ' + names.text.strip('\n')
                

    #finds next wallpaper listed on wallhaven
    def get_next_wall_info(self):

        #wallpaper to load 
        idx = self.wall_idx % self.walls_per_page

        #if onto next page go load it
        if (idx == 0):
            self.refresh_wall_list()

        #get wallpaper info
        wall = {'url': self.wall_urls[idx], 'tags': self.wall_tags[idx]}

        #increment
        self.wall_idx += 1

        return wall

    #get the wallpaper
    def get_wall(self, wall):
        url = urllib.urlopen(wall['url']).read()
        site = BeautifulSoup(url)

        wall['wallpaper'] = site.find('img', {'alt' : ''})['src']

        #give wallpaper a valid name (currently just using tags and id)        
        wall['name'] = wall['tags']
        wall['name'] = wall['name'] + ' ' + wall['wallpaper'].split('-')[-1]
        keepcharacters = (' ','.','_','-')
        wall['name'] = "".join(c for c in wall['name'] if c.isalnum() or c in keepcharacters).rstrip()

        return wall




class BlackList:

    def __init__(self, wall_dir):
        self.b_list = self.reload_black_list(wall_dir)

    #reload blacklist from file
    def reload_black_list(self, wall_dir):
        #read text file
        text_file = open(wall_dir + 'Settings\\Blacklist.txt', 'r')
        b_list = text_file.readlines()
        text_file.close()

        #convert to lowercase
        b_list[:] = [ item.lower().replace('\n','') for item in b_list if not (item.startswith('#') or item == '\n') ]
        return b_list

    #checks if a string of tags contains any blacklisted words
    def check(self, tags):
        #blank strings automatically fail
        if not tags:
            return True
        for b_tag in self.b_list:
            if b_tag in tags:
                return True
        return False



wall_dir = 'C:\\Users\\Zachary\\Pictures\\AutoWall\\'
set_wall = SetWallpaper(wall_dir)

time_out = 1800000

#loop forever
#while True:
    #set wallpaper
    #set_wall.set_next_wallpaper()
    #sleep for 10 min
    #time.sleep(600)

TRAY_TOOLTIP = 'AutoWall'
TRAY_ICON = wall_dir + 'Settings\\Icon.png'


def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.AppendItem(item)
    return item


class TaskBarIcon(wx.TaskBarIcon):
    def __init__(self):
        super(TaskBarIcon, self).__init__()
        self.set_icon(TRAY_ICON)
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

        #create timer
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.change_wall, self.timer)
        self.timer.Start(1000)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        create_menu_item(menu, 'Edit Blacklist', self.on_blacklist)
        menu.AppendSeparator()
        create_menu_item(menu, 'Next Image', self.on_next_image)
        menu.AppendSeparator()
        create_menu_item(menu, 'Pause', self.on_pause)
        menu.AppendSeparator()
        create_menu_item(menu, 'Exit', self.on_exit)
        return menu

    def set_icon(self, path):
        icon = wx.IconFromBitmap(wx.Bitmap(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def change_wall(self, event):
        set_wall.set_next_wallpaper()
        self.timer.Start(time_out)

    def on_left_down(self, event):
        print 'Tray icon was left-clicked.'

    def on_blacklist(self, event):
        os.startfile(wall_dir + 'Settings\\Blacklist.txt')

    def on_next_image(self,event):
        set_wall.set_next_wallpaper()
        self.timer.Start(time_out)

    def on_pause(self,event):
        self.timer.Stop()
        

    def on_exit(self, event):
        self.timer.Stop()
        wx.CallAfter(self.Destroy)


def main():
    app = wx.PySimpleApp()
    TaskBarIcon()
    app.MainLoop()


if __name__ == '__main__':
    main()


