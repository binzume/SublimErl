# ========================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ========================================================================

# globals
SUBLIMERL_VERSION = '0.5.1'

# imports
import sublime
import sublime_plugin
import os
import subprocess
import re


def readfiles_one_path_per_line(file_paths):
    concatenated_paths = []
    for file_path in file_paths:
        if os.path.exists(file_path):
            f = open(file_path, 'r')
            paths = f.read()
            f.close()
            paths = paths.split('\n')
            for path in paths:
                concatenated_paths.append(path.strip())
    return ':'.join(concatenated_paths)


def readfiles_exported_paths(file_paths):
    concatenated_paths = []
    for file_path in file_paths:
        if os.path.exists(file_path):
            p = subprocess.Popen(
                ". %s; echo $PATH" % file_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            path, stderr = p.communicate()
            concatenated_paths.append(path.strip())
    return ''.join(concatenated_paths)


def strip_code_for_parsing(code):
    code = strip_comments(code)
    code = strip_quoted_content(code)
    return strip_record_with_dots(code)


def strip_comments(code):
    # strip comments but keep the same character count
    return re.sub(re.compile(r"%(.*)\n"), lambda m: (len(m.group(0)) - 1) * ' ' + '\n', code)


def strip_quoted_content(code):
    # strip quoted content
    regex = re.compile(r"(\"([^\"]*)\")", re.MULTILINE + re.DOTALL)
    for m in regex.finditer(code):
        code = code[:m.start()] + (len(m.groups()[0]) * ' ') + code[m.end():]
    return code


def strip_record_with_dots(code):
    # strip records with dot notation
    return re.sub(re.compile(r"(\.[a-z]+)"), lambda m: len(m.group(0)) * ' ', code)


def get_erlang_module_name(view):
    # find module declaration and get module name
    module_region = view.find(
        r"^\s*-\s*module\s*\(\s*(?:[a-zA-Z0-9_]+)\s*\)\s*\.", 0)
    if module_region != None:
        m = re.match(
            r"^\s*-\s*module\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*\.", view.substr(module_region))
        return m.group(1)


def get_exe_path(name):
    retcode, data = execute_os_command('which %s' % name)
    data = data.strip()
    if retcode == 0 and len(data) > 0:
        return data


def execute_os_command(os_cmd):
    # start proc
    p = subprocess.Popen(
        os_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=get_env())
    stdout, stderr = p.communicate()
    return (p.returncode, stdout.decode('utf8'))


def shellquote(s):
    if  sublime.platform() != 'windows':
        return "'" + s.replace("'", "'\\''") + "'"
    else:
        return '"' + s.replace('"', '\\"') + '"'


def check_env():
    def test_path(path):
        return path != None and os.path.exists(path)

    settings = sublime.load_settings('SublimErl.sublime-settings')
    # erl check
    erl_path = get_erl_path()
    if test_path(erl_path) == False:
        log("Erlang binary (erl) cannot be found.")

    # escript check
    escript_path = get_escript_path()
    if test_path(escript_path) == False:
        log("Erlang binary (escript) cannot be found.")

    # rebar
    rebar_path = get_rebar_path()
    if test_path(rebar_path) == False:
        log("Rebar cannot be found, please download and install from <https://github.com/basho/rebar>.")
        return False

    # dialyzer check
    dialyzer_path = get_dialyzer_path()
    if test_path(dialyzer_path) == False:
        log("Erlang Dyalizer cannot be found.")
        return False


def get_plugin_path():
    plugin_path = os.path.join(sublime.packages_path(), 'SublimErl') # FIXME: theme failed on ST3 + Win.
    return plugin_path

def get_theme_path():
    # os.path.join(get_plugin_path(), "theme") # FIXME: theme failed on ST3 + Win.
    return "Packages/SublimErl/theme"

def get_completions_path():
    completions_path = os.path.join(get_plugin_path(), "completion")
    return completions_path


def get_support_path():
    support_path = os.path.join(get_plugin_path(), "support")
    return support_path


def get_erl_path():
    settings = sublime.load_settings('SublimErl.sublime-settings')
    erl_path = settings.get('erl_path', get_exe_path('erl'))
    return erl_path


def get_escript_path():
    settings = sublime.load_settings('SublimErl.sublime-settings')
    escript_path = settings.get(
        'escript_path', get_exe_path('escript'))
    return escript_path


def get_rebar_path():
    settings = sublime.load_settings('SublimErl.sublime-settings')
    rebar_path = settings.get(
        'rebar_path', get_exe_path('rebar'))
    return rebar_path


def get_dialyzer_path():
    settings = sublime.load_settings('SublimErl.sublime-settings')
    dialyzer_path = settings.get(
        'dialyzer_path', get_exe_path('dialyzer'))
    return dialyzer_path


def get_erlang_libs_path():
    # run escript to get erlang lib path
    os.chdir(get_support_path())
    escript_command = "sublimerl_utility.erl lib_dir"
    retcode, data = execute_os_command(
        '"%s" %s' % (get_escript_path(), escript_command))
    return data


def get_completion_skip_erlang_libs():
    settings = sublime.load_settings('SublimErl.sublime-settings')
    return settings.get(
        'completion_skip_erlang_libs', [])


def get_env():
    # TODO: enhance the finding of paths
    env = os.environ.copy()
    if sublime.platform() == 'osx':
        # get relevant file paths
        etc_paths = ['/etc/paths']
        for f in os.listdir('/etc/paths.d'):
            etc_paths.append(os.path.join('/etc/paths.d', f))
        # bash profile
        bash_profile_path = os.path.join(
            os.getenv('HOME'), '.bash_profile')
        # get env paths
        additional_paths = "%s:%s" % (readfiles_one_path_per_line(
            etc_paths), readfiles_exported_paths([bash_profile_path]))
        # add
        env['PATH'] = env['PATH'] + additional_paths
    return env


# project loader
class SublimErlProjectLoader():

    def __init__(self, view):
        # init
        self.view = view
        self.window = view.window()
        self.status_buffer = ''

        self.erlang_module_name = None
        self.project_root = None
        self.test_root = None
        self.app_name = None

        self.set_erlang_module_name()
        self.set_project_roots()
        self.set_app_name()

    def set_erlang_module_name(self):
        self.erlang_module_name = get_erlang_module_name(
            self.view)

    def set_project_roots(self):
        # get project & file roots
        current_file_path = os.path.dirname(self.view.file_name())
        project_root, file_test_root = self.find_project_roots(
            current_file_path)

        if project_root == file_test_root == None:
            self.project_root = self.test_root = os.path.abspath(
                os.path.dirname(self.view.file_name()))
        else:
            self.project_root = os.path.abspath(project_root)
            self.test_root = os.path.abspath(file_test_root)

    def find_project_roots(self, current_dir, project_root_candidate=None, file_test_root_candidate=None):
        # if rebar.config or an ebin directory exists, save as potential
        # candidate
        if os.path.exists(os.path.join(current_dir, 'rebar.config')) or os.path.exists(os.path.join(current_dir, 'ebin')):
            # set project root candidate
            project_root_candidate = current_dir
            # set test root candidate if none set yet
            if file_test_root_candidate == None:
                file_test_root_candidate = current_dir

        current_dir_split = current_dir.split(os.sep)
        # if went up to root, stop and return current candidate
        if len(current_dir_split) < 2:
            return (project_root_candidate, file_test_root_candidate)
        # walk up directory
        current_dir_split.pop()
        return self.find_project_roots(os.sep.join(current_dir_split), project_root_candidate, file_test_root_candidate)

    def set_app_name(self):
        # get app file
        src_path = os.path.join(self.test_root, 'src')
        if os.path.isdir(src_path):
            for f in os.listdir(src_path):
                if f.endswith('.app.src'):
                    app_file_path = os.path.join(src_path, f)
                    self.app_name = self.find_app_name(app_file_path)
                    return
        basename = os.path.basename(self.view.file_name())
        self.app_name = os.path.splitext(basename)[0]

    def find_app_name(self, app_file_path):
        f = open(app_file_path, 'rb')
        app_desc = f.read()
        f.close()
        m = re.search(
            r"{\s*application\s*,\s*('?[A-Za-z0-9_]+'?)\s*,\s*\[", app_desc.decode())
        if m:
            return m.group(1)

    def update_status(self):
        if len(self.status_buffer):
            sublime.status_message(self.status_buffer)
            self.status_buffer = ''

    def status(self, text):
        self.status_buffer += text
        sublime.set_timeout(self.update_status, 0)

    def log(self, text):
        pass

    def get_test_env(self):
        env = get_env().copy()
        env['PATH'] = "%s:%s:" % (env['PATH'], self.project_root)
        return env

    def compile_source(self, skip_deps=False):
        # compile to ebin
        options = 'skip_deps=true' if skip_deps else ''
        retcode, data = self.execute_os_command('%s compile %s' % (
            get_rebar_path(), options), dir_type='project', block=True, log=False)
        return (retcode, data)

    def shellquote(self, s):
        return shellquote(s)

    def execute_os_command(self, os_cmd, dir_type=None, block=False, log=True):
        # set dir
        if dir_type == 'project':
            os.chdir(self.project_root)
        elif dir_type == 'test':
            os.chdir(self.test_root)

        if log == True:
            self.log("%s$ %s\n\n" % (os.getcwd(), os_cmd))

        # start proc
        current_env = self.get_test_env()
        p = subprocess.Popen(os_cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=True, env=current_env)
        if block == True:
            stdout, stderr = p.communicate()
            return (p.returncode, stdout.decode('utf8'))
        else:
            stdout = []
            for line in p.stdout:
                self.log(line.decode('utf8'))
                stdout.append(line.decode('utf8'))
            return (p.returncode, ''.join(stdout))


# common text command class
class SublimErlTextCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        # run only if context matches
        if self._context_match():
            return self.run_command(edit)

    def _context_match(self):
        # context matches if lang is source.erlang
        caret = self.view.sel()[0].a
        if 'source.erlang' in self.view.scope_name(caret):
            return True
        else:
            return False

    def is_enabled(self):
        # context menu
        if self._context_match():
            return self.show_contextual_menu()
        else:
            return False

    def show_contextual_menu(self):
        # can be overridden
        return True
