#!/usr/bin/python

# PIRBOT: Simple jabber bot that polls the ring indicator signal on a serial port
# and notifies you if it changes
# example ~/.pirbotrc:
#
# user mybotname
# host myserver.mydomain.com
# pass mybotpasswd
# port /dev/ttyUSB0
# notify myself@myserver.mydomain.com/mysmartphonesjabberresourcename
#
# based on JabberBot: A simple jabber/xmpp bot framework
# Copyright (c) 2007-2011 Thomas Perl <thp.io/about>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# This is an example JabberBot that serves as broadcasting server.
# Users can subscribe/unsubscribe to messages and send messages 
# by using "broadcast". It also shows how to send message from 
# outside the main loop, so you can inject messages into the bot 
# from other threads or processes, too.
#

from jabberbot import JabberBot, botcmd
import xmpp.protocol
import os.path

import threading
import time 
import logging
import serial

class BroadcastingJabberBot(JabberBot):

    def __init__( self, conf, res = None):
        jid = conf["user"] + "@" + conf["host"]
        password = conf["pass"]
        self.conf = conf
        super( BroadcastingJabberBot, self).__init__( jid, password, res)

        # create console handler
        chandler = logging.StreamHandler()
        # create formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # add formatter to handler
        chandler.setFormatter(formatter)
        # add handler to logger
        self.log.addHandler(chandler)
        # set level to INFO
        self.log.setLevel(logging.INFO)

        self.users = []
        for k,v in self.conf.iteritems():
            if k == "notify":
                self.users.append(v)
        self.message_queue = ["Started!"]
        self.thread_killed = False

    @botcmd
    def subscribe( self, mess, args):
        """Subscribe to the broadcast list"""
        user = mess.getFrom()
        if user in self.users:
            return 'You are already subscribed.'
        else:
            self.users.append( user)
            self.log.info( '%s subscribed to the broadcast.' % user)
            return 'You are now subscribed.'

    @botcmd
    def unsubscribe( self, mess, args):
        """Unsubscribe from the broadcast list"""
        user = mess.getFrom()
        if not user in self.users:
            return 'You are not subscribed!'
        else:
            self.users.remove( user)
            self.log.info( '%s unsubscribed from the broadcast.' % user)
            return 'You are now unsubscribed.'
    
    # You can use the "hidden" parameter to hide the
    # command from JabberBot's 'help' list
    @botcmd(hidden=True)
    def broadcast( self, mess, args):
        """Sends out a broadcast, supply message as arguments (e.g. broadcast hello)"""
        self.message_queue.append( 'broadcast: %s (from %s)' % ( args, str(mess.getFrom()), ))
        self.log.info( '%s sent out a message to %d users.' % ( str(mess.getFrom()), len(self.users),))

    def idle_proc( self):
        if not len(self.message_queue):
            return

        message = self.message_queue.pop(0)

        if len(self.users):
            self.log.info('sending "%s" to %d user(s).' % ( message, len(self.users), ))
        for user in self.users:
            self.send( user, message)

    def MovementHandler(self, measurement):
        if measurement == True:
            msg = 'movement detected!'
        else:
            msg = 'no more movement'
        self.message_queue.append(msg)
        self.linestatus = measurement
        print msg

    def thread_proc( self):
        self.serial = serial.Serial(self.conf.get("port"))
        self.linestatus = True
        while not self.thread_killed:
            for i in range(60):
                time.sleep(1)
                measurement = self.serial.getRI()
                if self.linestatus != measurement: 
                    self.MovementHandler(not measurement)
                if self.thread_killed:
                    return



if __name__ == "__main__":
    import sys

    conffile = "~/.pirbotrc"
    f = open(os.path.expanduser(conffile),"r")
    conf = dict(map(lambda x: tuple(x.strip().split(None,1)), f.readlines()))
        
    if len(sys.argv) > 1:
        conf["port"] = sys.argv[1]

    bc = BroadcastingJabberBot(conf)
    th = threading.Thread(target = bc.thread_proc)
    try:
        bc.serve_forever( connect_callback = lambda: th.start())
    except xmpp.protocol.SystemShutdown, e:
        print "Shutting down due to error:",e
    print "Shutting down"
    bc.thread_killed = True
    th.join()

