#!/usr/bin/python3

import cv2
import numpy as np
import subprocess
import os, shutil
import paramiko
import configparser

from datetime import datetime
import smtplib as smtp
from email.mime.text import MIMEText
from email.header import Header   

config = configparser.ConfigParser()
config.read("tik_conf.ini") 
work_dir = config["path_to_file"]["work_dir"]
email = config["mail"]["email"]
password = config["mail"]["password"]
dest_email_2 = config["mail"]["dest_email_2"]
dest_email = config["mail"]["dest_email"]
suo_tik_login = config["tik"]["login"]
suo_tik_pass  = config["tik"]["password"]
stik_login = config["stik"]["login"]
stik_pass  = config["stik"]["password"]
vnc_pass = config["stik"]["vnc_password"]
body_letter = ""
ok_cnt = 0
ssh = paramiko.SSHClient()
fileName_log = str(datetime.now())

# Скриншоты с ТИКов собираются через vnccapture, а со СТИКов копированием картинки непосредственно.
# PNG файлы складываются в папку pict.
subprocess.run(['bash', work_dir + "vnc.sh", vnc_pass, stik_pass])

# Функция для подключения по ssh к неисправному устройству с целью перезагрузки.
def suo_tik_reboot(ip):
    response = os.system("fping " + ip + " >/dev/null")
    if response == 0:
        try:
            print('\nConnecting to ' + ip)
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username = suo_tik_login, password = suo_tik_pass, port = 22349)
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo -S reboot")
            ssh_stdin.write(suo_tik_pass + '\n')
            ssh_stdin.flush()
            output = ssh_stdout.read()
            print(output)
        except Exception as e:
            print(e)
    else:
        print(ip, "Unreachable")

def stik_reboot(ip):
    response = os.system("fping " + ip + " >/dev/null")
    if response == 0:
        try:
            print('\nConnecting to ' + ip)
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username = stik_login, password = stik_pass, port = 22349)
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo -S reboot")
            ssh_stdin.write(stik_pass + '\n')
            ssh_stdin.flush()
            output = ssh_stdout.read()
            print(output)
            print("command executed")
        except Exception as e:
            print(e)
    else:
        print(ip, "Unreachable")

# Функция для обнаружения целевого изображения внутри скриншота с экрана. Позаимствована.
def find_image(im, tpl):
    im = np.atleast_3d(im)
    tpl = np.atleast_3d(tpl)
    H, W, D = im.shape[:3]
    h, w = tpl.shape[:2]
    # Integral image and template sum per channel
    sat = im.cumsum(1).cumsum(0)
    tplsum = np.array([tpl[:, :, i].sum() for i in range(D)])
    # Calculate lookup table for all the possible windows
    iA, iB, iC, iD = sat[:-h, :-w], sat[:-h, w:], sat[h:, :-w], sat[h:, w:]
    lookup = iD - iB - iC + iA
  # Possible matches
    possible_match = np.where(np.logical_and.reduce([lookup[..., i] == tplsum[i] for i in range(D)]))
  # Find exact match
    for y, x in zip(*possible_match):
        if np.all(im[y+1:y+h+1, x+1:x+w+1] == tpl):
            return (y+1, x+1)
  # raise Exception("Image not found")

# Образец для поиска изображения.
tpl = cv2.imread(work_dir + 'service_regime.png', 1)

# Поочередно обрабатываются скриншоты, при совпадении - попытка перезагрузить ТИК, данные добавляются
#  в тело письма. При любом исходе - файлы перемещаются в папку moved.
for filename in os.listdir(work_dir + 'pict/'):
    if filename.endswith(".png"):
        im = cv2.imread(work_dir + 'pict/' + filename, 1)
        try:
            y, x = find_image(im, tpl)
            with open(work_dir + 'logs/' + fileName_log + '.log', 'a', encoding = 'utf-8') as file_log:
                print(str(filename[:-4]), file = file_log)
            body_letter += ("\n" + "ТИК " + str(filename[:-4]) + " в режиме обслуживания" + "\n")
            with open(work_dir + "suo_host.txt", 'r', encoding = 'utf8') as hosts:
                for id_str in hosts:
                    if id_str.rstrip() == str(filename[:-4]):
                        suo_tik_reboot(str(filename[:-4]))
                        body_letter += ("\n" + str(filename[:-4]) + " перезагружен" + "\n")
            with open(work_dir + "stik_host.txt", 'r', encoding = 'utf8') as hosts:
                for id_str in hosts:
                    if id_str.rstrip() == str(filename[:-4]):
                        stik_reboot(str(filename[:-4]))
                        body_letter += ("\n" + str(filename[:-4]) + " перезагружен" + "\n")
        except:
            print("Image not found")
            ok_cnt += 1
        shutil.move(work_dir + 'pict/' + filename, work_dir + 'pict/moved/' + filename)
                 
# Отправляется письмо с результатами работы.
text_email = u'В нормальном состоянии: \n'
body = text_email + str(ok_cnt) + body_letter
subject = u'Результаты обработки изображений с ТИКов'
msg = MIMEText(body, 'plain', 'utf-8')
msg['Subject'] = Header(subject, 'utf-8')        
msg['From'] = email
server = smtp.SMTP_SSL('smtp.yandex.com')
# server.set_debuglevel(1)
server.ehlo(email)
server.login(email, password)
server.auth_plain()
server.sendmail(email, dest_email, msg.as_string())
server.sendmail(email, dest_email_2, msg.as_string())
server.quit()
