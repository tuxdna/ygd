#!/usr/bin/python

# Copyright 2011 Saleem Ansari <tuxdna (at) gmail (dot) com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import errno
import os
import random
import re
import sys
import time

from optparse import OptionParser, OptionGroup, SUPPRESS_HELP
import getpass

from BeautifulSoup import BeautifulSoup
from BeautifulSoup import BeautifulStoneSoup
from twill import commands as tc

VERBOSE = 1
VERSION  = '0.1'
YG_BASE_URL='http://groups.yahoo.com/group'

HUMAN_WAIT = 1 # Amount of time it would take a human being to read a page
HUMAN_REFLEX = 5 # Amount of time it would take a human being to react to a page

attachment_nobody = r"""<br>
<i>[Attachment content not displayed.]</i><br><br>
</td></tr>
</table>"""

def mkdir_p(path):
    """
    Provide same functionality as shell command 'mkdir -p <path>'
    """
    try:
        os.makedirs(path)
    except OSError, exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise


def download_message(message_id, message_path, yahoo_group):
    mkdir_p(message_path)
    header_filepath = message_path+'/header'
    body_filepath = message_path+'/body'
    na_filepath = message_path+'/na'
    allhtml_filepath = message_path+'/all_html'

    if os.path.exists(message_path):
        if os.path.exists(na_filepath):
            return

    if os.path.exists(header_filepath) and os.path.exists(body_filepath):
        return

    msg_url = '%s/%s/message/%s?source=1&unwrap=1'%(YG_BASE_URL,yahoo_group,message_id)
    # sleep_duration = HUMAN_WAIT + random.randint(0,HUMAN_REFLEX)
    # if VERBOSE and sleep_duration:
    #     print ".... sleep % .... "%sleep_duration
    # time.sleep(sleep_duration)
    tc.go(msg_url)
    b = tc.get_browser()
    html = b.get_html()
    pattern_invalid = re.compile("Message (%s)? does not exist in %s"%(message_id, yahoo_group))
    m0 = re.search(pattern_invalid, b.get_html())

    f = open(allhtml_filepath, 'w')
    f.write(b.get_html())
    f.close()

    if m0:
        print "Message %s doesn't exist"%message_id
        f = open(na_filepath, 'w')
        f.close()
        return

    pattern_content = re.compile(r'<!-- start content include -->\s(.+?)\s<!-- end content include -->', re.DOTALL)
    m1 = re.search(pattern_content, html)

    if not m1:
        print "invalid format: html"
        return

    email_content = m1.group(1)
    mysoup = BeautifulSoup(email_content)
    source_content = mysoup.find('td', {'class': 'source user'}).__repr__()
    source_content = unicode(source_content, 'utf-8', errors='replace')
    source_content = source_content.encode('utf-8')

    m2 = re.search(re.compile(r'\s+(From .+?\s*)?<br />\s+<br />\s+(.+)</td>',re.DOTALL), source_content)

    if not m2:
        print "invalid format: email_content"
        f = open("source_content", 'w')
        f.write(source_content)
        f.close()
        sys.exit(1)
        return

    email_header = m2.group(1)
    new_header_lines = []
    for l in email_header.split('\n'):
        nl = re.sub(r'<a href=".+?>(.+?)<\/a>', lambda m: m.group(1), l)
        nl = re.sub(r'<br />$', '', nl)
        nl = BeautifulStoneSoup(nl, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        nl = nl.getText()
        new_header_lines.append(nl)

    email_header = '\n'.join(new_header_lines)

    email_body = m2.group(2)
    new_body_lines = []
    for l in email_body.split('\n'):
        nl = re.sub(r'<a href=".+?>(.+?)<\/a>', lambda m: m.group(1), l)
        nl = re.sub(r'<br />$', '', nl)
        nl = BeautifulStoneSoup(
            nl,
            convertEntities=BeautifulStoneSoup.HTML_ENTITIES
            )
        nl = nl.getText()
        new_body_lines.append(nl)

    email_body = '\n'.join(new_body_lines)

    f_header = open(header_filepath, 'w')
    f_header.write(email_header)
    f_header.close()

    f_body = open(body_filepath, 'w')
    email_body= email_body.encode('utf-8')
    f_body.write(email_body)
    f_body.close()



def start(args):
    parser = OptionParser(version=VERSION)
    parser.add_option("-p", "--password", help="account password")
    parser.add_option("-u", "--username", help="account user name")
    parser.add_option("-g", "--groupname", help="group name")

    (options, args) = parser.parse_args(args)
    password = options.password
    username = options.username
    yahoo_group = options.groupname
    if not (username and yahoo_group):
        parser.print_help()
        sys.exit(1)

    if not password:
        password = getpass.getpass()

    if not password:
        parser.print_help()
        sys.exit(1)

    yg_url = "%s/%s/"%(YG_BASE_URL, yahoo_group)

    tc.go(yg_url)
    tc.follow("Sign In")
    tc.formvalue(1, 'login', username)
    tc.formvalue(1, 'passwd', password)
    tc.submit()
    tc.follow("Messages")

    b = tc.get_browser()
    browser_title =  b.get_title()
    m = re.search(r'Messages : (\d+)-(\d+) of (\d+)', browser_title)

    if not m:
        print "regular expression failed"
        sys.exit(1)

    start, end, total_messages = m.groups()

    for i in range(int(total_messages)):
        message_id = i + 1
        message_path = '%s/%s'%(yahoo_group, message_id)
        download_message(message_id, message_path, yahoo_group)


if __name__ == '__main__':
    start(sys.argv)
