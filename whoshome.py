#!/usr/bin/env python3

'''
Who's Home
by Brandon Asuncion <me@brandonasuncion.tech>

Uses an ASUS router's web interface to determine active wireless devices.
'''
import time

import requests
import re
import json
from base64 import b64encode
from collections import defaultdict

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

### START CONFIG ###

USERNAME = "admin"
PASSWORD = "admin@12"
GATEWAY = "a0756eb35481f5fcb3da11a82511625c4.asuscomm.com:8443"
PORT = "8443"

BLACKLIST = {
    'E8:D8:19:3F:DE:4B',
    '74:40:BE:E9:FC:F6',
}

### END CONFIG ###

safeInt = lambda i: int(float(i)) if i.strip() else 0


def getActiveClients():
    s = requests.Session()

    loginData = {
        'group_id': '',
        'action_mode': '',
        'action_script': '',
        'action_wait': '5',
        'current_page': 'Main_Login.asp',
        'next_page': 'index.asp',
        'login_authorization': b64encode("{}:{}".format(USERNAME, PASSWORD).encode())
    }

    reqHeaders = {'Referer': "https://{}/".format(GATEWAY)}

    # Login to router
    s.post("https://{}/login.cgi".format(GATEWAY), data=loginData, headers=reqHeaders, verify=False)

    # Get client data
    clientData = s.get("https://{}/update_clients.asp".format(GATEWAY), headers=reqHeaders, verify=False).text

    # Logout
    s.get("https://{}/Logout.asp".format(GATEWAY), headers=reqHeaders, verify=False)

    activeClients = defaultdict(lambda: {})
    stripped_data = clientData[clientData.find('{'):clientData.rfind('}') + 1].replace('\n', '').replace('\\n', '')
    fixed_json = stripped_data.replace('{fromNetworkmapd', '{"fromNetworkmapd"') \
        .replace(',nmpClient', ',"nmpClient"')
    clientLists = json.loads(fixed_json)
    for k, v in clientLists['fromNetworkmapd'][0].items():
        if k != 'maclist':
            activeClients[k]['Tx'] = safeInt(v['curTx'])
            activeClients[k]['Rx'] = safeInt(v['curRx'])
            activeClients[k]['accessTime'] = v['wlConnectTime']
            activeClients[k]['name'] = v['name']
            activeClients[k]['nickName'] = v['nickName']
            activeClients[k]['isWireless'] = v['isWL'] != '0'
            activeClients[k]['RSSI'] = v['rssi']

    return activeClients


def sendEmail(to, subject, text):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.ehlo()
    s.starttls()
    s.login('tahaeghtesad@gmail.com', 'duwmgkaqyhgjifya')
    msg = MIMEMultipart()
    msg['From'] = 'tahaeghtesad@gmail.com'
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(text, 'plain'))

    s.send_message(msg)


def notifyEvent(status, mac, info):
    recipients = ['tahaeghtesad@gmail.com']
    print(f'{info["nickName"]} has {"left" if status == 1 else "entered"} the house')

    for to in recipients:
        sendEmail(to, f'{info["nickName"]} has {"left" if status == 1 else "entered"} the house', f'{mac}\n{info}')

def checkIncomingOutgoing():
    iter = 0
    clients = getActiveClients()
    previousMacs = clients.keys()
    while True:
        time.sleep(10)
        activeClients = getActiveClients()
        clients.update(activeClients)
        currentMacs = activeClients.keys()
        for entering in currentMacs - previousMacs:
            if entering not in BLACKLIST:
                notifyEvent(0, entering, clients[entering])
        for leaving in previousMacs - currentMacs:
            if leaving not in BLACKLIST:
                notifyEvent(1, leaving, clients[leaving])
        previousMacs = currentMacs

        if iter % 180 == 0:
            sendEmail('tahaeghtesad@gmail.com', 'WhosHomeReport', json.dumps(activeClients, indent=4))

        iter += 1


if __name__ == '__main__':
    sendEmail('tahaeghtesad@gmail.com', 'WhosHome Scraper Started', 'Let the scrapers scrape.')
    checkIncomingOutgoing()


