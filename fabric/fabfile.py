#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import xml.etree.ElementTree as ET
from fabric.api import *
from socket import *


def pingit(host, port=22, verbose=False):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect((host, port))
        return True
    except:
        if verbose:
            print "Host", host, "is down\n"
        return False
    finally:
        sock.close()


class HostsCmds():
    def cmds(self, **args):
        self.cxml = args['cxml']
        self.cmd_line = args['cmd_line']
        self.cmd_list = list()

        if self.cmd_line <> None:
            self.cmd_list.append(self.cmd_line)
        else:
            self.cmdXML = ET.parse(self.cxml + '.xml').getroot()
            for cmdList in self.cmdXML.findall('cmdList'):
                for cmd in cmdList.findall('cmd'):
                    self.cmd_list.append(cmd.text)
        return self.cmd_list

    def hosts(self, **args):
        self.hxml = args['hxml']
        self.host_list = list()

        if len(env.hosts) > 0:
            self.host_list = env.hosts
        else:
            self.hostsXML = ET.parse(self.hxml + '.xml').getroot()
            for hostDesc in self.hostsXML.findall('hostList'):
                for host in hostDesc.findall('host'):
                    self.host_list.append(host.text)
        return self.host_list


class RunCmds():
    __cmd_result = list()
    __result_buffer = dict()
    __file_list = dict()
    def __init__(self, **args):
        self.hosts = args['hosts']
        self.commands = args['commands']
        self.warn_only = args['warn_only']
        self.quiet = args['quiet']
        self.mode = args['mode']
        try:
            self.reset_results = args['reset_results']
            if self.reset_results == 'yes':
                self.__cmd_result = list()
                self.__result_buffer = dict()
        except KeyError:
            pass
        print "Tryb pracy: " + self.mode

    @serial
    def sexec(self):
        temp = dict()
        if pingit(env.host_string):
            for cmd in self.commands:
                self.__result_buffer[cmd] = run(cmd, shell=False, warn_only=self.warn_only, )
                temp[env.host_string] = self.__result_buffer.copy()
            self.__cmd_result.append(temp.copy())
            return self.__result_buffer

    #  @parallel(pool_size=10) # Run on as many as 10 hosts at once
    #  do rozkumania, ew jako parametr
    @parallel
    def pexec(self):
        if pingit(env.host_string):
            for cmd in self.commands:
                self.__result_buffer[cmd] = run(cmd, shell=False, warn_only=self.warn_only, )
            return self.__result_buffer

    def go(self):
        if self.quiet:
            with settings(hide('running', 'commands', 'stdout', 'stderr')):
                if self.mode == "parallel":
                    stdout = execute(self.pexec, hosts=self.hosts)
                    self.__cmd_result.append(stdout.copy())
                else:
                    stdout = execute(self.sexec, hosts=self.hosts)
        else:
            if self.mode == "parallel":
                stdout = execute(self.pexec, hosts=self.hosts)
                self.__cmd_result.append(stdout.copy())
            else:
                stdout = execute(self.sexec, hosts=self.hosts)
        return stdout

    def show_result(self, format_='l'):
        for h in self.hosts:
            if format_ == 'l':  # lista
                print h + ':'
                for el in self.__cmd_result:
                    try:
                        if el[h] is None:
                            print 'is down'
                        else:
                           for key_ in el[h].keys():
                               print key_ + ':', el[h][key_].return_code
                               print el[h][key_]
                    except KeyError:
                        pass
                print
            elif format_ == 't':  # tabela
                print h + "\t",
                for el in self.__cmd_result:
                    try:
                        if el[h] is None:
                            print 'is down'
                        else:
                            for key_ in el[h].keys():
                                print key_ + ':', el[h][key_].return_code, "\t",
                    except KeyError:
                        pass
                print
            elif format_ == 'e':  # edycja plików
                for el in self.__cmd_result:
                    try:
                        if el[h] is None:
                            pass
                        else:
                            for key_ in el[h].keys():
                                self.__file_list[h] = el[h][key_]
                    except KeyError:
                        pass

        return self.__file_list


@task
def acmd(c=None, cl='cmds', hl='hosts', un='root', v='1', e='1', f='l', m='s'):
    """

    podstawowa forma wykonywania komend na zdalnych hostach.

    :param c: komenda z linii poleceń, domyślnie: brak
    :param cl: plik z listą komend, domyślnie: cmds.xml (bez rozszerzenia) w bieżącym katalogu
    :param hl: plik z listą hostów, domyślnie: hosts.xml (bez rozszerzenia) w bieżącym katalogu
    :param un: użytkownik, domyślnie: root
    :param v: [0|inne] - wypisuje komunikaty fabric. Domyślnie <> 0
    :param e: [0|inne] - kończy działanie przy błędzie zdalnej komendy (reszta hostów nie jest przetwarzana).
                         Domyślnie <> 0
    :param f: [l|t] - format wyjścia (Lista/Tabela). Domyślnie l
    :param m: [p|inne] tryb wykonywania komend (Parallel/Serial). Domyślnie <> p (serial).
              Uwaga. W trybie paralell muszą być wymienione klucze ssh.
    :return:

    komendy i hosty podane z linii poleceń mają priorytet nad plikowymi.
    Podanie, np. komend w linii poleceń i pliku z listą komend spowoduje
    wykonanie komend z linii poleceń i pominięcie komend z pliku.

    """

    env.user = un
    hstcmd = HostsCmds()
    hosts = hstcmd.hosts(hxml=hl)
    cmds = hstcmd.cmds(cmd_line=c, cxml=cl)

    rc = RunCmds(hosts=hosts, commands=cmds, quiet=(False if v<>'0' else True),warn_only=(False if e<>'0' else True), mode=('parallel' if m=='p' else 'serial'))
    rc.go()
    rc.show_result(f)

    quit()


@task
def scmd(c=None, cl='cmds', hl='hosts', un='root', v='0', e='0', f='l'):
    """

    wykonywanie komend na zdalnych hostach w trybie "szeregowym"

    :param c: komenda z linii poleceń, domyślnie: brak
    :param cl: plik z listą komend, domyślnie: cmds.xml (bez rozszerzenia) w bieżącym katalogu
    :param hl: plik z listą hostów, domyślnie: hosts.xml (bez rozszerzenia) w bieżącym katalogu
    :param un: użytkownik, domyślnie: root
    :param v: [0|inne] - wypisuje komunikaty fabric. Domyślnie  0
    :param e: [0|inne] - kończy działanie przy błędzie zdalnej komendy (reszta hostów nie jest przetwarzana).
                         Domyślnie  0
    :param f: [l|t] - format wyjścia (Lista/Tabela). Domyślnie l
    :return:

    komendy i hosty podane z linii poleceń mają priorytet nad plikowymi.
    Podanie, np. komend w linii poleceń i pliku z listą komend spowoduje
    wykonanie komend z linii poleceń i pominięcie komend z pliku.

    """

    env.user = un
    hstcmd = HostsCmds()
    hosts = hstcmd.hosts(hxml=hl)
    cmds = hstcmd.cmds(cmd_line=c, cxml=cl)

    rc = RunCmds(hosts=hosts,
                 commands=cmds,
                 quiet=(False if v<>'0' else True),
                 warn_only=(False if e<>'0' else True,),
                 mode='serial',
                 reset_results="yes")
    rc.go()
    rc.show_result(f)

    quit()


@task
def pcmd(c=None, cl='cmds', hl='hosts', un='root', v='0', e='0', f='l'):
    """

    wykonywanie komend na zdalnych hostach w trybie "równoległym"
    Uwaga. Żeby zabanglało muszą być wymienione klucze ssh.

    :param c: komenda z linii poleceń, domyślnie: brak
    :param cl: plik z listą komend, domyślnie: cmds.xml (bez rozszerzenia) w bieżącym katalogu
    :param hl: plik z listą hostów, domyślnie: hosts.xml (bez rozszerzenia) w bieżącym katalogu
    :param un: użytkownik, domyślnie: root
    :param v: [0|inne] - wypisuje komunikaty fabric. Domyślnie  0
    :param e: [0|inne] - kończy działanie przy błędzie zdalnej komendy (reszta hostów nie jest przetwarzana).
                         Domyślnie  0
    :param f: [l|t] - format wyjścia (Lista/Tabela). Domyślnie l
    :return:

    komendy i hosty podane z linii poleceń mają priorytet nad plikowymi.
    Podanie, np. komend w linii poleceń i pliku z listą komend spowoduje
    wykonanie komend z linii poleceń i pominięcie komend z pliku.

    """

    env.user = un
    hstcmd = HostsCmds()
    hosts = hstcmd.hosts(hxml=hl)
    cmds = hstcmd.cmds(cmd_line=c, cxml=cl)

    rc = RunCmds(hosts=hosts, commands=cmds, quiet=(False if v<>'0' else True),warn_only=(False if e<>'0' else True), mode='parallel')
    rc.go()
    rc.show_result(f)

    quit()


@task
def lcmd(cmd=None, hl='hosts', un='root', v='0', e='0', f='l', m='s'):
    """

    wykonywanie lokalnej komendy na zdalnych hostach

    Opis:
    plik lokalny jest przesyłany na zdalne hosty do katalogu $HOME/.fabric z maską 700
    następnie jest wykonywany (można przekazać parametry) i usuwany.
    jest to kombinacja zadań send i pcmd

    :param cmd:  komenda (skrypt lokalny)
    :param hl:  plik z listą hostów, domyślnie: hosts.xml (bez rozszerzenia) w bieżącym katalogu
    :param un:  użytkownik, domyślnie: root
    :param v:  [0|inne] - wypisuje komunikaty fabric. Domyślnie  0
    :param e:  [0|inne] - kończy działanie przy błędzie zdalnej komendy (reszta hostów nie jest przetwarzana).
                          Domyślnie  0
    :param f:  [l|t] - format wyjścia (Lista/Tabela). Domyślnie l
    :param m: [p|inne] tryb wykonywania komend (Parallel/Serial). Domyślnie <> p (serial).
              Uwaga. W trybie paralell muszą być wymienione klucze ssh.
    :return:
    """

    env.user = un
    hstcmd = HostsCmds()
    hosts = hstcmd.hosts(hxml=hl)
    rc = RunCmds(hosts=hosts, commands=['mkdir .fabric || true'], quiet=True,warn_only=True, mode='parallel')
    rc.go()

    if (cmd is None):
        print "Nie podano nazwy pliku(ów)"
        quit()
    cmd = cmd.strip()
    local_cmd_file = cmd.split()[0]
    remote_cmd_file = ".fabric/" + os.path.basename(local_cmd_file)
    cmd_args = ' ' + ' '.join(cmd.split()[1:])

    send(lf=local_cmd_file, rf=remote_cmd_file, hl=hl, un=un, m='0700', p='0')
    print

    rc = RunCmds(
        hosts=hosts,
        commands=[remote_cmd_file + cmd_args],
        quiet=(False if v<>'0' else True),
        warn_only=(False if e<>'0' else True),
        mode=('parallel' if m=='p' else 'serial'),
        reset_results='yes'
    )
    rc.go()
    rc.show_result(f)

    rc = RunCmds(hosts=hosts, commands=['rm -f ' + remote_cmd_file], quiet=True,warn_only=True, mode='parallel')
    rc.go()

    quit()


@task
def upgr(c='1'):
    """

    upgrade pakietów debiana

    :param c: [0|1|2]
           c=0 apt-get -y upgrade w trybie równoległym
           c=1 apt-get -y upgrade w trybie szeregowym (domyślne)
           c=2 apt-get    upgrade w trybie szeregowym
    :return:
    """

    env.user = 'root'
    hstcmd = HostsCmds()
    hosts = hstcmd.hosts(hxml='hosts')
    if c == '0':
        cmds = ['(export DEBIAN_FRONTEND=noninteractive; apt-get upgrade -q -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold")']
        mode ='parallel'
    elif c == '1':
        cmds = ['(export DEBIAN_FRONTEND=noninteractive; apt-get upgrade -q -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold")']
        mode ='serial'
    elif c == '2':
        cmds = ['apt-get upgrade']
        mode ='serial'
    else:
        print "Błąd parametru"
        quit()

    rc = RunCmds(hosts=hosts, commands=cmds, quiet=False,warn_only=True, mode=mode)
    rc.go()
    rc.show_result('l')

    quit()


@task
def send(lf=None, rf=None, hl='hosts', un='root',m=None, p='1'):
    """

    przesyła plik(i)/katalogi na zdalne hosty

    :param lf: nazwa pliku lokalnego
    :param rf: nazwa pliku zdalnego. Domyślnie: brak. Wtedy wyliczane: basename(lf)
               i przesyłane do katalogu domowego użytkownika.
    :param hl: plik z listą hostów, domyślnie: hosts.xml (bez rozszerzenia) w bieżącym katalogu.
    :param un: użytkownik, domyślnie: root
    :param m:  maska pliku (jak chmod). Domyślnie: None (kopiowana maska lf)
    :param p:  [0|inne] - potwierdzenie przesłania pliku(ów) dla każdego hosta. Domyślnie: 1.
    :return:
    """

    env.user = un
    hstcmd = HostsCmds()
    hosts = hstcmd.hosts(hxml=hl)

    if (lf is None):
        print "Nie podano nazwy pliku(ów)"
        quit()

    if rf is None:
        rf = os.path.basename(lf)

    if p <> '0':
        continue_ = 'n'
    else:
        continue_ = 'a'
    for host in hosts:
        env.host_string = host

        if continue_ <> 'a':
            with settings(abort_on_prompts=False):
                print host + ':'
                continue_ = prompt('Kontynuować? (y/n/a/q)',default='n' ,validate=r'[y|n|a|q]')

        if continue_ in ('a', 'y'):
            if pingit(host, verbose=True):
                if m is None:
                    put(lf, rf, mirror_local_mode=True)
                else:
                    put(lf, rf, mode=int(m, 8))
        elif continue_ == 'q':
            quit()

    #quit()

@task
def edit(fn=None, hl="hosts", un='root', ed='t', m='a'):
    """

    edycja pliku(ów) na zdalnych hostach

    :param fn: nazwa pliku(ów). Musi być nazwą w pełni kwalifikowaną (absolutną).
    :param hl: plik z listą hostów, domyślnie: hosts.xml (bez rozszerzenia) w bieżącym katalogu.
    :param un: użytkownik, domyślnie: root
    :param ed:[t|p|<command>] komenda edycji plików. Domyślnie: t.
               t - 'screen vim -p'
               g - 'gvim --nofork -p'
               command - użytkownika
    :param m:[a|h|n] Domyślnie: a.
           m=a wszystkie pliki jednocześnie
           m=h z podziałem na hosty
           m=n edycja "zewnętrzna" (tylko ściąga i rozpakowuje pliki.
               Czeka na zakończenie edycji w zewnętrznym edytorze)
    :return:

    komendy i hosty podane z linii poleceń mają priorytet nad plikowymi.
    Podanie, np. komend w linii poleceń i pliku z listą komend spowoduje
    wykonanie komend z linii poleceń i pominięcie komend z pliku.

    Opis:
        paralell
         1. taruje wybrane pliki do $HOME/.fabric/fabric.$$.tar
        serial:
         2. ściąga *.tar na lokalny dysk
         3. zmienia nazwy zdalnych plików na *.tar.YYYY-MM-DD_HH-MM-SS
         4. rozpakowuje lokalne archiwa *.tar
         5. edytuje pliki
         6. aktualizuje lokalne archiwa
         7. przesyła archiwa *.tar na zdalne hosty
         8. rozpakowuje zdalne archiwa ze ścieżką bezwzględną
         9. przywraca uprawnienia na zdalnych hostach (tylko dla un=root)
        10. usuwa lokalne pliki (ściągnięte *tar i rozpakowane)

    Uwagi:
       przywracanie uprawnień odbywa się w całym drzewie  basename fn (getfacl/setfacl). Jeśli pomiedzy
       tymi operacjami jakiś proces zmieni uprawnienia w drzewie to zostaną one nadpisane. Nie bardzo wiem,
       jak to obejść.
    """

    env.user = un
    hstcmd = HostsCmds()
    hosts = hstcmd.hosts(hxml=hl)

    if ed == 't':
        ed = 'screen vim -p'
    elif ed == 'g':
        ed = 'gvim --nofork -p'

    if (fn is None):
        print "Nie podano nazwy pliku(ów)"
        return
    else:
        files = fn.split()
        for fname in files:
            if fname[0] != '/':
                print fname + " musi mieć nazwę w pełni kwalifikowaną (absolutną).", "\n"
                quit()

    log_lst = list()

    cmd = ['mkdir .fabric']
    log_lst.append('remote: ' + str(cmd))
    rc = RunCmds(hosts=hosts, commands=cmd, quiet=True,warn_only=True, mode='parallel')
    rc.go()
    cmd = ["(/usr/bin/getfacl -Rp $(dirname " + fn + ") > .fabric/saved_permissions.$$; tar --create --file=.fabric/fabric.$$.tar " + fn + ' >/dev/null 2>&1; ls -1 .fabric/fabric.$$.tar)']
    log_lst.append('remote: ' + str(cmd))
    rc = RunCmds(hosts=hosts, commands=cmd, quiet=True,warn_only=True, mode='parallel', reset_results='yes')
    rc.go()

    hosts_files = rc.show_result('e')  # słownik host:archiwum

    #  rozpakowanie i edycja plików
    edit_list = list()   # lista wywołań edytora w przypadku edycji z podziałem na hosty
    edit_cmd = ed + ' '  # komenda wywołania edytora w przypadku edycji hurtowej
    ctime = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time()))
    for host in hosts_files.keys():
        env.host_string = host
        tar_file = os.path.basename(hosts_files[host])
        get(hosts_files[host])

        cmd = "mv " + hosts_files[host] + " " + hosts_files[host] + '.' + ctime
        log_lst.append('remote: ' + str(cmd))
        run(cmd, shell=False, quiet=False, warn_only=True)

        cmd = "tar --directory=" + env.host_string + " --extract --verbose --file=" + env.host_string + "/" + tar_file
        log_lst.append('local: ' + str(cmd))
        local(cmd)

        cmd = "find ./" + env.host_string + " -type f -! -name " + tar_file + " | sort"
        edit_list.append(cmd)
        found_files = local(cmd,capture=True)
        cmd = ed + ' '
        for line in found_files.splitlines():
            cmd += line + ' '
            edit_cmd += line + ' '
        edit_list.append(cmd)

    log_lst.append('local: ' + str(edit_cmd))
    if 'a' == m:
        local(edit_cmd)
    elif 'h' == m:
        for cmd in edit_list:
            local(cmd, shell='/bin/bash')
    else:
        with settings(abort_on_prompts=False):
            print "pliki ściągnięte i rozpakowane"
            edit_external = prompt('Kontynuować?',default='n' ,validate=r'[t|n]')
            if edit_external <> 't':
                print "edycja przerwana, usuń pliki i katalogi ręcznie"
                quit()

    #  aktualizacja lokalnych archiwów, przesłanie na zdalne hosty
    #  rozpakowanie zdalnych archiwów, przywrócenie uprawnień
    continue_ = 'n'
    for host in hosts_files.keys():
        env.host_string = host
        tar_file = os.path.basename(hosts_files[host])
        pid = tar_file.split('.')[1]

        cmd = "cd " + host + "; find . -maxdepth 1 -type d -printf '%f\\n' | sort"
        log_lst.append('local: ' + str(cmd))
        found_files = local(cmd, capture=True)

        first = True
        cmd = "cd " + host + "; tar --create --verbose --file=" + tar_file + ' '
        for line in found_files.splitlines():
            if first:
                first = False
            else:
                cmd += line + ' '
        log_lst.append('local: ' + str(cmd))
        local(cmd)

        if continue_ <> 'a':
             with settings(abort_on_prompts=False):
                 print host + ':'
                 continue_ = prompt('Kontynuować? (y/n/a/q)',default='n' ,validate=r'[y|n|a|q]')

        if continue_ in ('a', 'y'):
            put(host + "/" + tar_file, ".fabric/" + tar_file)
            cmd = "(tar --overwrite --absolute-names --extract --verbose --directory=/ --file=.fabric/" + tar_file
            if un == 'root':
                cmd += "; /usr/bin/setfacl --restore=.fabric/saved_permissions." + pid
            cmd += ")"
            log_lst.append('remote: ' + str(cmd))
            run(cmd,shell=False, quiet=False, warn_only=False)
        elif continue_ == 'q':
            break

    # usunięcie lokalnych plików
    for host in hosts_files.keys():
        cmd = "rm -rvf " + host
        log_lst.append('local: ' + str(cmd))
        local(cmd)

    print "\n###########################################################################"
    for line in log_lst:
        print line
    print "###########################################################################\n"
    quit()


@task
def down(o='-r', hl="hosts", un="root"):
    """

    Wykonuje shutdown [opions] na zdalnych hostach (z potwierdzeniem). Czas +1 jest dopisywany automatycznie

    :param hl: plik z listą hostów, domyślnie: hosts.xml (bez rozszerzenia) w bieżącym katalogu.
    :param un: użytkownik, domyślnie: root
    :param o: opcje (jak w shutdown), domyślnie -r
    :return:
    """

    env.user = un
    hstcmd = HostsCmds()
    hosts = hstcmd.hosts(hxml=hl)
    cmd = 'shutdown ' + o + ' +1'

    print hosts, cmd
    continue_ = 'n'
    for host in hosts:
        env.host_string = host

        print host + ':', cmd
        if continue_ <> 'a':
            with settings(abort_on_prompts=False):
                continue_ = prompt('Kontynuować? (y/n/a/q)',default='n' ,validate=r'[y|n|a|q]')

        if continue_ in ('a', 'y'):
            if pingit(host, verbose=True):
                try:
                    run(cmd, shell=False, pty=False, quiet=True, warn_only=True, timeout=1)
                except:
                    pass
        elif continue_ == 'q':
            quit()

    quit()

