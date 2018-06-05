#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# original software is "pingman".
# original software is "deadman".
# Copyright 2015 Interop Tokyo ShowNet team All Rights Reserved.
# Copyright 2017 KC TechTeam Teramoto Shinya
# upa@haeena.net
# adding Function "log"
#Developer : tera@tech-KCrent
#Naming Person : kuma@tech-KCrent

import re
import os
import sys
import time
import commands
import socket
import curses
import thread
import locale
import datetime
from optparse import OptionParser

# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.mime.text import MIMEText
from datetime import datetime


locale.setlocale(locale.LC_ALL, "ja_JP.UTF-8")


TITLE_PROGNAME = "Teraping"
TITLE_VERSION = "[ver 0.1.0]"
TITLE_VERTIC_LENGTH = 4

try :
    TITLE_HOSTINFO = "From: %s (%s)" % (
        commands.getoutput ("hostname"),
        socket.gethostbyname (commands.getoutput ("hostname")))
except :
    TITLE_HOSTINFO = "From: %s" % commands.getoutput ("hostname")



#ping emviroment function
ARROW = " > "
REAR  = "   "
PING_INTERVAL = 0.05
PING_ALLTARGET_INTERVAL = 1
MAX_HOSTNAME_LENGTH = 20
MAX_ADDRESS_LENGTH = 40
RESULT_STR_LENGTH = 10

DEFAULT_COLOR = 1
UP_COLOR = 2
DOWN_COLOR = 3

RTT_SCALE = 6
CONFIGFILE = "deadman.conf"

SSH_CONNECT_TIMEOUT = 3

OSNAME = commands.getoutput ("uname -s")


PING_TIMEOUT = 1

PING_SUCCESS      = 0
PING_FAILED       = -1
PING_SSH_TIMEOUT  = -2
PING_SSH_FAILED   = -3

LOGDIR = ""

class PingResult :

    def __init__ (self, success = False, errcode = PING_FAILED,
                  rtt = 0.0, ttl = 0) :
        self.success = success
        self.errcode = errcode
        self.rtt = rtt
        self.ttl = ttl
        return
    

class PingTarget :

    def __init__ (self, name, address, osname, relay = None, source = None) :

        self.name = name
        self.addr = address
        self.relay = relay
        self.state = False
        self.loss = 0
        self.lossrate = 0.0
        self.rtt = 0 # current RTT
        self.tot = 0 # total of all RTT
        self.avg = 0 # average of all RTT
        self.snt = 0 # number of sent ping
        self.ttl = 0 # last ttl   
	self.count = 0
	self.error = 0
     	self.result = []

        self.ping = Ping (self.addr, osname, relay = relay,
                          source = source)

        return

    def send (self) :

        res = self.ping.send ()

        self.snt += 1

        if res.success :
            # Ping Success
            self.state = True
            self.rtt = res.rtt
            self.tot += res.rtt
            self.avg = (self.tot) / self.snt
            self.ttl = res.ttl
	    self.count = 0
	    self.error = self.error + 0

        else :
            # Ping Failed
            self.loss += 1
            self.state = False

	    self.count = self.count + 1
	    self.error = self.error + 1

        self.lossrate = float (self.loss) / float (self.snt) * 100.00
        self.result.insert (0, self.get_result_char (res))

	if self.count == 6:
					from_address  = 'example1@mail.co.jp'
					to_address    = 'example2@mail.co.jp'
					IP_address = self.count
					

					# メール本文
					msg = MIMEText( "testmail_from_python\n" + \
							"IP:" + str(self.addr) + "\n" + \
							"Date:" + datetime.now().strftime("%Y/%m/%d %H:%M:%S") + "\n" + \
							"Device:" + str(self.name))

					# 件名、宛先
					msg['Subject'] = '【TeraPing】Alert - ' + str(self.name)
					msg['From']    = from_address
					msg['To']      = to_address

					# Send the message via our own SMTP server, but don't include the envelope header.
					s = smtplib.SMTP()
					s.connect()
					s.sendmail( from_address, to_address, msg.as_string() )
					s.close()

				
	else :
		return


        while len (self.result) > RESULT_STR_LENGTH :
            self.result.pop ()

        return

    def get_result_char (self, res) :

        if res.errcode == PING_SSH_TIMEOUT :
            # ssh timeout
            return "t"

        if res.errcode == PING_SSH_FAILED :
            # ssh failed
            return "s"

        if res.errcode == PING_FAILED :
            # ping timeout
            return "X"

#pingのグラフ化
#基準値からの応答時間の表現

        if res.rtt < RTT_SCALE * 1 : return "▁"
        if res.rtt < RTT_SCALE * 2 : return "▂"
        if res.rtt < RTT_SCALE * 3 : return "▃"
        if res.rtt < RTT_SCALE * 4 : return "▄"
        if res.rtt < RTT_SCALE * 5 : return "▅"
        if res.rtt < RTT_SCALE * 6 : return "▆"
        if res.rtt < RTT_SCALE * 7 : return "▇"

        return "█"


    def refresh (self) :
        self.state = None
        self.lossrate = 0.0
        self.loss = 0
        self.rtt = 0
        self.tot = 0
        self.avg = 0
        self.snt = 0
        self.ttl = 0
        self.result = []
	self.count = 0
	self.error = 0

        return


class Ping :

    def __init__ (self, addr, osname, timeout = PING_TIMEOUT, relay = None,
                  source = None) :

        # XXX: 'timeout' must overwrite pingcmdstr -W or -i options

        self.addr = addr
        self.osname = osname
        self.relay = relay
        self.source = source

#IPアドレスの判断
        ipv = whichipversion (self.addr)
        if ipv == 4 :
            self.ipversion = 4
        elif ipv == 6 :
            self.ipversion = 6
        else :
		ipdn = socket.gethostbyname_ex(self.addr)
		dnsip = str(ipdn[2])
		addr = dnsip[2:-2]
		ipv = whichipversion (addr)
        	if ipv == 4 :
            		self.ipversion = 4
       		elif ipv == 6 :
          		self.ipversion = 6
            	else :
            			self.ipversion = -1
            			raise RuntimeError ("invalid IP address \"%s\"" % self.addr)

        self.pingcmdstr = pingcmdstrings (osname, ipv)

        return

    def send (self) :

        viacmd = ""
        sourcecmd = ""
        if self.relay and self.relay.has_key("via") :
            if self.relay["via"] == "snmp" :
                ## SNMP
                return self.sendSnmpPing()

            if self.relay["via"] == "netns" :
                ## ping via Network Namespace
                viacmd = "ip netns exec %s " % self.relay["relay"]

        elif self.relay :
            ## SSH
            viacmd = ("ssh -o ConnectTimeout=%d -o StrictHostKeyChecking=no " %
                      SSH_CONNECT_TIMEOUT)
            if self.relay.has_key ("key") :
                viacmd += "-i %s " % self.relay["key"]
            if self.relay.has_key ("user") :
                viacmd += "-l %s " % self.relay["user"]
            if not self.relay.has_key ("relay") :
                raise RuntimeError ("\"relay\" is not specified for %s" %
                                    self.addr)
            viacmd += "%s " % self.relay["relay"]

        if self.source :
            if self.osname == "Linux" :
                sourcecmd += " %s " % ("-I %s" % self.source)
            elif self.osname == "Darwin" :
                sourcecmd += " %s " % ("-S %s" % self.source)
            else :
                raise RuntimeError ("\"source\" not supported on %s" %
                                    self.osname)

        pingcmd = viacmd + self.pingcmdstr + sourcecmd + " %s" % self.addr

        result = commands.getoutput (pingcmd)

        rttm = re.search (r'time=(\d+\.\d+)', result)
        if not rttm:
            rttm = re.search (r'time=(\d+)', result)

        ttlm = re.search (r'ttl=(\d+)', result)
        if not ttlm:
            ttlm = re.search (r'hlim=(\d+)', result)

        res = PingResult ()

        if rttm :
            res.success = True
            res.errcode = PING_SUCCESS
            res.rtt = float (rttm.group (1))
            if ttlm :
                res.ttl = int (ttlm.group (1))
            else :
                res.ttl = -1

        if not rttm :
            res.sucess = False
            if re.search (r'ping', result) :
                res.errcode = PING_FAILED
            if re.search (r'No route to host', result) :
                res.errcode = PING_FAILED
            if re.search (r'Operation timed out', result) :
                res.errcode = PING_SSH_TIMEOUT
            if not re.search (r'PING', result) :
                res.errcode = PING_SSH_FAILED

            res.errcode = PING_FAILED

        return res

    def sendSnmpPing (self) :
        if not self.relay.has_key("community") :
            raise RuntimeError ("\"community\" is not specified for %s" %
                                self.addr)
        community = self.relay["community"]
        community = community.replace("\\", "\\\\")
        community = community.replace("'", "\\'")
        snmpcmd = "snmpping -Cc1 -v 2c -c \'%s\' " % community
        if not self.relay.has_key("relay") :
            raise RuntimeError ("\"relay\" is not specified for %s" %
                                self.addr)
        snmpcmd += " %s " % self.relay["relay"]

        pingcmd = snmpcmd + " %s" % self.addr

        result = commands.getoutput (pingcmd)

        rttm = re.search (r'rtt min/avg/max/stddev = (\d+)', result)

        res = PingResult ()

        if rttm :
            res.success = True
            res.errcode = PING_SUCCESS
            res.rtt = float (rttm.group (1))
            res.ttl = -1

        if not rttm :
            res.sucess = False
            res.errcode = PING_FAILED

        return res


class CursesCtrl () :

    def __init__ (self, stdscr) :
        self.stdscr = stdscr
        return

    def key_thread (self, *args) :

        while True :
            ch = self.stdscr.getch ()

            if ch == ord ('r') :
                num = 0
                for target in args :
                    num += 1
                    target.refresh ()
                    self.erase_pingtarget (num)
                    self.print_pingtarget (target, num)


    def update_info (self, targets) :
        # update start point and string length

        self.y, self.x = self.stdscr.getmaxyx ()

        # update arrow
        self.start_arrow = 0
        self.length_arrow = len (ARROW)

        # update hostname
        hlen = len ("HOSTNAME ")
        for target in targets :
            if hlen < len (target.name) : hlen = len (target.name)
        if hlen > MAX_HOSTNAME_LENGTH : hlen = MAX_HOSTNAME_LENGTH

        self.start_hostname = self.start_arrow + self.length_arrow
        self.length_hostname = hlen

        # update address
        alen = len ("ADDRESS ")
        for target in targets :
            if alen < len (target.addr) : alen = len (target.addr)
        if alen > MAX_ADDRESS_LENGTH : alen = MAX_ADDRESS_LENGTH
        else : alen += 5

        self.start_address = self.start_hostname + self.length_hostname + 1
        self.length_address = alen

        # update reference
        self.ref_start = self.start_address + self.length_address + 1
        self.ref_length = len (" LOSS  TTL  RTT  AVG  SNT  ERR")

        # update result
        self.res_start = self.ref_start + self.ref_length + 2
        self.res_length = self.x - (self.ref_start + self.ref_length + 2)

        # reverse
        if self.res_length < 10 :
            rev = 10 - self.res_length + len (ARROW)
            self.ref_start -= rev
            self.res_start -= rev
            self.res_length = 10

        global RESULT_STR_LENGTH
        RESULT_STR_LENGTH = self.res_length

        return


    def refresh (self) :

        self.stdscr.refresh ()
        return

    def waddstr (self, *args) :

        # wrapper for stdscr.addstr

        try :
            if len (args) == 3 :
                self.stdscr.addstr (args[0], args[1], args[2])
            if len (args) > 3 :
                self.stdscr.addstr (args[0], args[1], args[2], args[3])
        except curses.error :
            pass


    def print_title (self) :

        # Print Program name on center of top line
        spacelen = int ((self.x - len (TITLE_PROGNAME)) / 2)
        self.waddstr (0, spacelen, TITLE_PROGNAME, curses.A_BOLD)

        # Print hostname and version number
        self.waddstr (1, self.start_hostname, TITLE_HOSTINFO,
                            curses.A_BOLD)
        spacelen = self.x - (len (ARROW) + len (TITLE_VERSION))
        self.waddstr (1, spacelen, TITLE_VERSION, curses.A_BOLD)
        self.waddstr (2, len (ARROW),
                            "RTT Scale %dms. Keys: (r)efresh" % RTT_SCALE)
        self.stdscr.move (0, 0)
        self.stdscr.refresh ()
        return

    def erase_title (self) :
        space = ""
        for x in range (self.x) :
            space += " "
        self.waddstr (0, 0, space)
        self.waddstr (1, 0, space)
        self.waddstr (2, 0, space)
        return

    def print_reference (self) :
        hostname_str = "HOSTNAME"
        address_str = "ADDRESS"
        values_str = " LOSS  TTL  RTT  AVG  SNT  ERR  RESULT"

        # Print reference hostname and address
        self.waddstr (TITLE_VERTIC_LENGTH, len (ARROW),
                      hostname_str, curses.A_BOLD)
        self.waddstr (TITLE_VERTIC_LENGTH, self.start_address,
                      address_str, curses.A_BOLD)

        # Print references of values
        self.waddstr (TITLE_VERTIC_LENGTH, self.ref_start,
                      values_str, curses.A_BOLD)

        self.stdscr.move (0, 0)
        self.stdscr.refresh ()
        return

    def erase_reference (self) :
        space = ""
        for x in range (self.x) :
            space += " "
        self.waddstr (TITLE_VERTIC_LENGTH, 0, space)
        return

    def print_pingtarget (self, target, number) :

        if target.state :
            line_color = curses.color_pair (DEFAULT_COLOR)
        else :
            line_color = curses.A_BOLD

        linenum = number + TITLE_VERTIC_LENGTH

	#hostname & Address
	hostname_str = target.name
	address_str = target.addr
	self.error = target.error

        # Print values
        values_str = " %3d%% %4d %4d %4d %4d %4d  " % (int(target.lossrate),
                                                   target.ttl,
                                                   target.rtt,
                                                   target.avg,
                                                   target.snt,
						   target.error)

#Fileメソッド
	f = open('test.csv', 'a') 
	f.write(datetime.now().strftime("%Y/%m/%d %H:%M:%S") + "\t" + hostname_str + "\t" + address_str + "\t" + values_str + "\n")
	f.close()

        # Print ping line
        self.waddstr (linenum, self.start_hostname,
                            target.name[0:self.length_hostname], line_color)
        self.waddstr (linenum, self.start_address,
                            target.addr[0:self.length_address], line_color)

        self.waddstr (linenum, self.ref_start, values_str, line_color)


        for n in range (len (target.result)) :
            if target.result[n] != "X" and target.result[n] != "t" and target.result[n] != "s":
                color = curses.color_pair (UP_COLOR)
            else :
                color = curses.color_pair (DOWN_COLOR)

            y, x = self.stdscr.getmaxyx()
            if self.res_start + n > x :
                continue
            self.waddstr (linenum, self.res_start + n,
                                target.result[n], color)

        y, x = self.stdscr.getmaxyx()
        self.waddstr (linenum, x - len (REAR), REAR)
        
        if LOGDIR in sys.argv :
            filepath = LOGDIR + "/" + target.name
            if os.path.isdir(LOGDIR) == False:
                os.makedirs(LOGDIR)
            f = open(filepath, 'a')
            fline = str(datetime.datetime.now()) + " " + str(target.rtt) + " " + str(target.avg) + " " + str(target.snt) + "\n";
            f.write(fline)
            f.close()
        else :
            pass 

        self.stdscr.move (0, 0)
        self.stdscr.refresh ()

        return
        
    def print_arrow (self, number) :
        linenum = number + TITLE_VERTIC_LENGTH

        self.waddstr (linenum, self.start_arrow, ARROW)
        self.stdscr.move (0, 0)
        self.stdscr.refresh ()
        return

    def erase_arrow (self, number) :
        linenum = number + TITLE_VERTIC_LENGTH

        space_str = ""
        for x in range (len (ARROW)) :
            space_str += " "

        self.waddstr (linenum, self.start_arrow, space_str)
        self.stdscr.move (0, 0)
        self.stdscr.refresh ()
        return

    def erase_pingtarget (self, number) :
        linenum = number + TITLE_VERTIC_LENGTH
        space = ""
        for x in range (self.x) :
            space += " "
        self.waddstr (linenum, 2, space)
        return


class Deadman :

    def __init__ (self, stdscr, configfile) :

        self.targets = []
        self.curs = CursesCtrl (stdscr)
        self.targetlist = self.gettargetlist (configfile)

        for name, addr, relay, source in self.targetlist :
            if relay.has_key ("os") :
                osname = relay['os']
            else :
                osname = OSNAME

            self.targets.append (PingTarget (name, addr, osname,
                                             relay = relay, source = source))

        self.curs.update_info (self.targets)

        self.curs.print_title ()

        return


    def main (self) :

        thread.start_new_thread (self.curs.key_thread, tuple (self.targets))

        # print blank line
        num = 0
        for target in self.targets :
            num += 1
            self.curs.print_pingtarget (target, num)

        while True :

            self.curs.update_info (self.targets)
            self.curs.erase_title ()
            self.curs.print_title ()
            self.curs.erase_reference ()
            self.curs.print_reference ()

            num = 0
            for target in self.targets :
                num += 1

                self.curs.print_arrow (num)
                target.send ()
                self.curs.erase_pingtarget (num)
                self.curs.print_pingtarget (target, num)
                time.sleep (PING_INTERVAL)
                self.curs.erase_arrow (num)

            self.curs.print_arrow (num)
            time.sleep (PING_ALLTARGET_INTERVAL)
            self.curs.erase_arrow (num)
            self.curs.erase_pingtarget (num + 1)


    def gettargetlist (self, configfile) :

        try :
            cf = open (configfile, "r")
        except :
            sys.exit (r'can not open config file "%s"' % (configfile))

        targetlist = []

        for line in cf :

            line = re.sub ('\t', ' ', line)
            line = re.sub ('\s+', ' ', line)
            line = re.sub ('#.*', '', line)
            line = line.strip (' \r\n')
            line = line.rstrip (' \r\n')

            if line == "" :
                continue

            ss = line.split (' ')
            name = ss.pop (0)
            addr = ss.pop (0)
            source = None
            relay = {}
            for s in ss :
                key, value = s.split ("=")
                if key in ("os", "relay", "via", "community", "netns") :
                    relay[key] = value
                elif key == "source" :
                    source = value

            targetlist.append ([name, addr, relay, source])

        cf.close ()

        return targetlist



# mics
def whichipversion (addr) :

    if re.match (r'^(\d{1,3}\.){3,3}\d{1,3}$', addr)  :
        return 4

    if re.match (r'((([0-9a-f]{1,4}:){7}([0-9a-f]{1,4}|:))|(([0-9a-f]{1,4}:){6}(:[0-9a-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9a-f]{1,4}:){5}(((:[0-9a-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9a-f]{1,4}:){4}(((:[0-9a-f]{1,4}){1,3})|((:[0-9a-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){3}(((:[0-9a-f]{1,4}){1,4})|((:[0-9a-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){2}(((:[0-9a-f]{1,4}){1,5})|((:[0-9a-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){1}(((:[0-9a-f]{1,4}){1,6})|((:[0-9a-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9a-f]{1,4}){1,7})|((:[0-9a-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$', addr) :
        return 6

    return -1


def pingcmdstrings (osname, ipv) :

    # XXX : add new osname (uname -s) to support new OS.
    if osname == "Linux" :
        if ipv == 4 : return "ping -W 1 -c 1"
        if ipv == 6 : return "ping6 -i 1 -c 1"
    elif osname == "Darwin" :
        if ipv == 4 : return "ping -W 1000 -c 1"
        if ipv == 6 : return "ping6 -i 1 -c 1"

    return None



def main (stdscr) :

    curses.start_color ()
    curses.use_default_colors ()
    curses.init_pair (DEFAULT_COLOR, -1, -1)
    curses.init_pair (UP_COLOR, curses.COLOR_GREEN, -1)
    curses.init_pair (DOWN_COLOR, curses.COLOR_RED, -1)

    """
    XXX: parse and validating config file shoud be done before curses.wrapper.
    """

    deadman = Deadman (stdscr, CONFIGFILE)
    deadman.main ()

    return



if __name__ == '__main__' :

    if not pingcmdstrings (OSNAME, 4) :
        print ("%s is not supported" % OSNAME)
        sys.exit (0)

    desc = "usage : %prog [options] configfile"
    parser = OptionParser (desc)

    parser.add_option (
        '-s', '--scale', type = "int", default = RTT_SCALE, dest = 'scale',
        help = 'scale of ping RTT bar gap.'
    )
    parser.add_option (
        '-l', '--logging', type = "string", default = None, dest = 'logdir',
        help = 'logging.'
    )

    (options, args) = parser.parse_args ()
    
    RTT_SCALE = options.scale
    LOGDIR    = options.logdir

    try :
        CONFIGFILE = args.pop ()
    except :
        print "config file is not specified. deadman [-s scale] [-l logdir] configfile"
        sys.exit ()

    try :
        curses.wrapper (main)

    except KeyboardInterrupt :
        sys.exit(0)
