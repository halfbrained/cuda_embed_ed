import os
import time
import re

from cudatext import *
from cudax_lib import get_translation, _json_loads

_   = get_translation(__file__)  # I18N

fn_config = os.path.join(app_path(APP_DIR_SETTINGS), 'plugins.ini')
fn_config_patters = os.path.join(app_path(APP_DIR_SETTINGS), 'cuda_embed_ed_patterns.json')
_plugin_dir = os.path.dirname(os.path.realpath(__file__))
fn_default_patterns = os.path.join(_plugin_dir, 'data', 'cuda_embed_ed_patterns.json')


ED_MAX_LINES = 24
PATTERNS = {}

BTN_SAVE = 'btn_em_save'
BTN_CLOSE = 'btn_em_close'
BTN_NEW_TAB = 'to_new_tab'

GAP_TAG = app_proc(PROC_GET_UNIQUE_TAG, '')
USER_DIR = os.path.expanduser('~')

def collapse_path(path):
    if path  and  (path + os.sep).startswith(USER_DIR + os.sep):
        path = path.replace(USER_DIR, '~', 1)
    return path


_lex_cache = {}

def detect_lex(path):
    if path in _lex_cache:
        return _lex_cache[path]

    _lex = lexer_proc(LEXER_DETECT, path)
    if isinstance(_lex, tuple):
        caption = _('Choose lexer for: {}').format(os.path.basename(path))
        ind = dlg_menu(DMENU_LIST, _lex, caption=caption)
        if ind is not None:
            _lex = _lex[ind]
        else:
            _lex = None

    _lex_cache[path] = _lex
    return _lex


class Command:

    def __init__(self):
        self._ed_hints = {} # editor handle -> Hint()

        self.load_config()

    def load_config(self):
        global ED_MAX_LINES

        ED_MAX_LINES = int(ini_read(fn_config, 'embedded_editor', 'editor_max_lines', str(ED_MAX_LINES)))

        # load lexer path-patterns, compile regexes
        PATTERNS.clear()

        _patterns_path = fn_config_patters  if os.path.exists(fn_config_patters) else  fn_default_patterns
        with open(_patterns_path, 'r', encoding='utf-8') as f:
            s_patterns = f.read()

        jpatterns = _json_loads(s_patterns)
        for name,group in jpatterns.copy().items():
            ps = group.get('path_patterns')
            if isinstance(ps, list):
                ps_copy = ps[:]
                ps.clear()

                for pattern in ps_copy:
                    if '(?P<path>' not in pattern:
                        print(_('NOTE: pattern ({}) in group "{}" is missing a named group "path":')
                                    .format(pattern, name))
                        continue

                    try:
                        ps.append(re.compile(pattern))
                    except re.error:
                        print(_('NOTE: failed to compile pattern in group "{}": {}').format(name, pattern))

                # bring lexer names to lower-case
                if 'lexers' in group:
                    lexers = group['lexers']
                    if isinstance(lexers, list):
                        group['lexers'] = set(map(str.lower,  lexers))
                    else:
                        del jpatterns[name]
                        print(_('NOTE: invalid "lexers" in group: {}. Should be a list').format(name))
            else:
                del jpatterns[name]
                print(_('NOTE: invalid patterns in group: {}. Should be a list').format(name))

        PATTERNS.update(jpatterns)


    def config(self):
        ini_write(fn_config, 'embedded_editor', 'editor_max_lines', str(ED_MAX_LINES))
        file_open(fn_config)

    def config_patterns(self):
        if not os.path.exists(fn_config_patters):
            with open(fn_default_patterns, 'r', encoding='utf-8') as f:
                s_patterns = f.read()
            with open(fn_config_patters, 'w', encoding='utf-8') as f:
                f.write(s_patterns)

        file_open(fn_config_patters)


    def on_close_pre(self, ed_self):
        """ if closed Editor has 'embed' with unsaved text - give prompt to save|cancel|ignore
        """
        embed = self._get_ed_embed(ed_self)
        if embed  and  embed.is_visible:
            if embed.text_modified:
                cancel_close = embed.save_text(dlg=True)
                if cancel_close:
                    return False    # "return false to cancel closing"

            # did not cancel 'close' -> destroy embed
            embed.hide(animate=False, skip_save=True) # destroy dialog
            h_ed = ed_self.get_prop(PROP_HANDLE_SELF)
            del self._ed_hints[h_ed] # destroy `Hint` object

    # callback proxy for dialog buttons
    def on_dlg_btn(self, id_dlg, id_ctl, data='', info=''):
        embed = self._get_ed_embed(ed)
        if embed  and  embed.is_visible:
            embed.on_btn(info)

    # timer callback
    def on_restore_pos(self, data='', info=''):
        embed = self._get_ed_embed(ed)
        if embed  and  embed.is_visible:
            embed.restore_scroll_pos(delay=False)

    def _get_caret_filepath(self, caret_x, caret_y):
        """ find matching pattern in line under caret, extract file-path
        """
        tline = ed.get_text_line(caret_y)    # text line
        for name,dpatterns in PATTERNS.items(): # test each pattern group again the line
            lex = ed.get_prop(PROP_LEXER_FILE)
            if lex:
                lex = lex.lower()
            pattern_lexers = dpatterns.get('lexers')
            if pattern_lexers  and  lex not in pattern_lexers:
                continue

            ps = dpatterns.get('path_patterns')
            for pattern in ps:
                for match in pattern.finditer(tline): # check if match contains the caret position
                    span = match.span()
                    if span[0] <= caret_x <= span[1]: # caret is in match's range
                        try:
                            return match.group('path')
                        except IndexError:
                            pass    # error is printed in `load_config()`


        tl,tr = tline[:caret_x], tline[caret_x:]  # text to left|right of caret
        if '"' in tl  and '"' in tr:
            fn_start = tl.rindex('"') + 1
            fn_end = caret_x + tr.index('"')
            return tline[fn_start:fn_end]

    def _get_ed_embed(self, _ed, create=False):
        h_ed = _ed.get_prop(PROP_HANDLE_SELF)

        if h_ed not in self._ed_hints  and  create:
            self._ed_hints[h_ed] = Hint()

        return self._ed_hints.get(h_ed)


    # menu command
    def toggle(self):
        embed = self._get_ed_embed(ed, create=True)

        # hiding #####
        if embed.is_visible:
            embed.hide()
        # showing #####
        else:
            ed_fn = ed.get_filename()
            if not ed_fn: #
                return

            carets = ed.get_carets()
            if len(carets) != 1  or  carets[0][3] != -1: # restrict to single caret, no selection
                return
            caret_x, caret_y = carets[0][:2]       # caret pos

            path_str = self._get_caret_filepath(caret_x, caret_y)
            if not path_str:
                msg_status(_('No embedded file-path was found'))
                return
            full_path = os.path.join(os.path.dirname(ed_fn), path_str)

            if os.path.exists(full_path):
                embed.show(full_path, nline=caret_y, caption=path_str)

                msg_status(_("Opened '{}' in embedded window").format(path_str))
            else:
                msg_status(_('Linked file was not found: {}').format(full_path))


VK_ESCAPE = 27

FORM_W = 550
FORM_H = 350
BUTTON_H = app_proc(PROC_GET_GUI_HEIGHT, 'button')
HIDE_ANIM_DURATION = 0.05 # sec

class Hint:
    def __init__(self):
        self.h = None
        self.nline = None

        self._enabled = False   # to skip commands during animation
        self._sb_fn_modified = None
        self._scroll_poss = {} # path -> (scroll x, scroll y)

        self._h_to_free = None

    @property
    def is_visible(self):
        if self.h is None:
            return False
        return dlg_proc(self.h, DLG_PROP_GET)['vis']

    @property
    def text_modified(self):
        return self.ed.get_prop(PROP_MODIFIED)

    def init_form(self):
        global FORM_H

        _cell_w, cell_h = ed.get_prop(PROP_CELL_SIZE)
        FORM_H = ED_MAX_LINES*cell_h + BUTTON_H

        h = dlg_proc(0, DLG_CREATE)

        colors = app_proc(PROC_THEME_UI_DICT_GET, '')
        color_form_bg   = colors['TabBorderActive']['color']
        color_ed_bg     = colors['EdGutterBg']['color']
        self.color_tab_font            = colors['TabFont']['color']
        self.color_tab_font_modified   = colors['TabFontMod']['color']
        self.color_tab_back            = colors['TabActive']['color']
        self.color_tab_back_passive    = colors['TabPassive']['color']

        dlg_proc(h, DLG_PROP_SET, prop={
                'w': FORM_W,
                'border': False,
                'color': color_form_bg,
                'keypreview': True,
                'on_key_down': self.on_key,
                })

        self._n_sb = dlg_proc(h, DLG_CTL_ADD, 'statusbar')
        dlg_proc(h, DLG_CTL_PROP_SET, index=self._n_sb, prop={
                'align': ALIGN_BOTTOM,
                'sp_l': 1,
                'sp_r': 1,
                'sp_b': 1,
                'h': BUTTON_H, 'h_max': BUTTON_H,
                })
        self._h_sb = dlg_proc(h, DLG_CTL_HANDLE, index=self._n_sb)

        n = dlg_proc(h, DLG_CTL_ADD, 'editor')
        dlg_proc(h, DLG_CTL_PROP_SET, index=n, prop={
                'align': ALIGN_CLIENT,
                'h': FORM_H,
                'sp_r': 2,
                'on_click_link': self.on_click_link,
                'on_change': self.on_text_change,
                })
        h_ed = dlg_proc(h, DLG_CTL_HANDLE, index=n)
        edt = Editor(h_ed)
        self._n_ed = n

        edt.set_prop(PROP_LAST_LINE_ON_TOP, False)
        edt.set_prop(PROP_COLOR, (COLOR_ID_TextBg, color_ed_bg))

        return h, edt


    def show(self, full_path, nline, caption=None):

        if not full_path  or  not nline  or  not os.path.exists(full_path):
            return

        if self._h_to_free:
            dlg_proc(self._h_to_free, DLG_FREE)
            self._h_to_free = None

        if self.h is None:
            self.h, self.ed = self.init_form()


        with open(full_path, 'r', encoding='utf-8') as f:
            text = f.read()

        self.full_path = full_path
        self.nline = nline
        self.caption = caption

        # dialog Editor setup #####
        _lex = detect_lex(full_path)
        self.ed.set_prop(PROP_LEXER_FILE, _lex)

        self.ed.set_text_all(text)
        self.ed.set_prop(PROP_MODIFIED, False)
        self.ed.set_prop(PROP_LINE_TOP, 0)

        self.reset_line_states(LINESTATE_NORMAL)
        self.restore_scroll_pos()

        # calculate dialog position and dimensions: x,y, h,w #####
        l,t,r,b = ed.get_prop(PROP_RECT_TEXT)
        cell_w, cell_h = ed.get_prop(PROP_CELL_SIZE)
        ed_size_x = r - l # text area sizes - to not obscure other ed-controls

        caret_loc_px = ed.convert(CONVERT_CARET_TO_PIXELS, x=1, y=nline)
        y0,y1 = caret_loc_px[1], b
        h = min(FORM_H,  y1-y0 - cell_h)
        w = ed_size_x # full width


        # Gap #####
        ed.gap(GAP_DELETE_BY_TAG, 0, 0, tag=GAP_TAG)
        ed.gap(GAP_ADD, nline, self.h, size=h, tag=GAP_TAG)
        # Dlg #####
        dlg_proc(self.h, DLG_PROP_SET, prop={
                'p': ed.get_prop(PROP_HANDLE_SELF ), #set parent to Editor handle
                #'x': l, # `l` to skip editor's gutter -- doesnt work with gap-embeded dlg
                #'y': y,
                'w': w,
                'h': h,
                })

        self.update_statusbar()
        self._sb_fn_modified = False

        self._enabled = True
        dlg_proc(self.h, DLG_SHOW_NONMODAL)

    def update_statusbar(self):
        """ [save][ ... filename ... ][close]
        """
        def add_statusbar_cell(caption, cellwidth, callback_name=None, hint=None): #SKIP
            cellind = statusbar_proc(self._h_sb, STATUSBAR_ADD_CELL, index=-1)
            statusbar_proc(self._h_sb, STATUSBAR_SET_CELL_TEXT, index=cellind, value=caption)

            if cellwidth: # close,save - width and center
                statusbar_proc(self._h_sb, STATUSBAR_SET_CELL_SIZE, index=cellind, value=cellwidth)
                statusbar_proc(self._h_sb, STATUSBAR_SET_CELL_ALIGN, index=cellind, value='C')
            else: # autostretch
                statusbar_proc(self._h_sb, STATUSBAR_SET_CELL_AUTOSTRETCH, index=cellind, value=True)

            if hint:
                statusbar_proc(self._h_sb,  STATUSBAR_SET_CELL_HINT, index=cellind, value=hint)

            fg = self.color_tab_font
            if callback_name:
                bg = self.color_tab_back

                callback = callback_fstr.format(callback_name)
                statusbar_proc(self._h_sb, STATUSBAR_SET_CELL_CALLBACK, index=cellind, value=callback)
            else:
                bg = self.color_tab_back_passive
                if self.text_modified:
                    fg = self.color_tab_font_modified

            statusbar_proc(self._h_sb,  STATUSBAR_SET_CELL_COLOR_BACK, index=cellind, value=bg)
            statusbar_proc(self._h_sb,  STATUSBAR_SET_CELL_COLOR_FONT, index=cellind, value=fg)
        #end add_statusbar_cell

        statusbar_proc(self._h_sb, STATUSBAR_DELETE_ALL)

        cellwidth = BUTTON_H*4
        callback_fstr = 'module=cuda_embed_ed;cmd=on_dlg_btn;info={};'
        collapsed_path = collapse_path(self.full_path)

        add_statusbar_cell(_('To new tab'), cellwidth, callback_name=BTN_NEW_TAB)
        add_statusbar_cell(_('Save'), cellwidth, callback_name=BTN_SAVE)
        _caption = (self.caption  or  collapsed_path)
        if self.text_modified:
            _caption = '*' + _caption
        add_statusbar_cell(_caption, cellwidth=None, hint=collapsed_path)
        add_statusbar_cell(_('Close'), cellwidth, callback_name=BTN_CLOSE)

    def on_text_change(self, id_dlg, id_ctl, data='', info=''):
        if self._sb_fn_modified  is not  self.text_modified:
            self._sb_fn_modified = self.text_modified
            self.update_statusbar()

    def on_btn(self, name):
        if   name == BTN_SAVE:
            self.save_text()
        elif name == BTN_CLOSE:
            self.hide()
        elif name == BTN_NEW_TAB:
            self.to_new_tab()


    def on_click_link(self, id_dlg, id_ctl, data='', info=''):
        import webbrowser

        if data:
            webbrowser.open(data)

    def on_key(self, id_dlg, id_ctl, data='', info=''):
        key_code = id_ctl
        state = data

        if key_code == VK_ESCAPE  and  not state:  # <escape> in filter - clear
            self.hide()
            return False


    def to_new_tab(self):
        if not self.text_modified:
            self.hide(animate=False)

        scroll_pos = self._scroll_poss.get(self.full_path)
        carets = self.ed.get_carets()

        file_open(self.full_path)

        if scroll_pos:
            ed.set_prop(PROP_SCROLL_VERT, scroll_pos[1])
            ed.set_prop(PROP_SCROLL_HORZ, scroll_pos[0])

        if carets:
            ed.set_caret(*carets[0], options=CARET_OPTION_NO_SCROLL)
            for caret in carets[1:]:
                ed.set_caret(*caret, id=CARET_ADD, options=CARET_OPTION_NO_SCROLL)


    def save_text(self, dlg=False):
        """ returns: cancel save
        """
        if dlg  and  self.text_modified:
            _filename = os.path.basename(self.full_path)
            msg = _('Text is modified:\n{}\n\nSave it first?').format(_filename)
            result = msg_box(msg, MB_YESNOCANCEL or MB_ICONQUESTION)

            if result == ID_NO:
                return False    # not cancel closing
            elif result == ID_CANCEL:
                return True     # cancel closing
        #end if dlg

        text = self.ed.get_text_all()

        with open(self.full_path, 'w', encoding='utf-8') as f:
            f.write(text)

        self.ed.set_prop(PROP_MODIFIED, False)
        self.update_statusbar()
        self.reset_line_states(LINESTATE_SAVED)


    def hide(self, animate=True, skip_save=False):
        if not self.h:
            return

        if not skip_save:
            cancel = self.save_text(dlg=True)
            if cancel:
                return

        self._enabled = False
        self.save_scroll_pos()

        if animate:
            start_time = time.time()
            end_time = start_time + HIDE_ANIM_DURATION
            while time.time() < end_time:
                _fraction = (time.time() - start_time) / HIDE_ANIM_DURATION
                _fraction = (1-_fraction)**2
                new_h = int(_fraction*FORM_H + 1)

                # Gap #####
                ed.gap(GAP_ADD, self.nline, 0, size=new_h, tag=GAP_TAG)
                # Dlg #####
                dlg_proc(self.h, DLG_PROP_SET, prop={'h': new_h,})

                app_idle(False)
        #end if

        # remove dialog
        ed.gap(GAP_DELETE_BY_TAG, 0, 0, tag=GAP_TAG)
        dlg_proc(self.h, DLG_HIDE)
        #NOTE: access violation if freeing dialog from button event -> free on next show()
        #dlg_proc(self.h, DLG_FREE)
        self._h_to_free = self.h
        self.h = None

        ed.focus()

    def save_scroll_pos(self):
        if self.full_path and self.h:
            scrol_pos = (self.ed.get_prop(PROP_SCROLL_HORZ), self.ed.get_prop(PROP_SCROLL_VERT))
            self._scroll_poss[self.full_path] = scrol_pos

    def restore_scroll_pos(self, delay=True):
        """ starts timer to restore scroplll position
        """
        if delay:
            callback = 'module=cuda_embed_ed;cmd=on_restore_pos;'
            timer_proc(TIMER_START_ONE, callback, 0)

        else:
            _scroll_pos = self._scroll_poss.get(self.full_path)
            if _scroll_pos:
                self.ed.set_prop(PROP_SCROLL_VERT, _scroll_pos[1])
                self.ed.set_prop(PROP_SCROLL_HORZ, _scroll_pos[0])

    def reset_line_states(self, target_state):
        """ reset modified lines states to one of `LINESTATE_nnn`
        """
        for nline,state in enumerate(self.ed.get_prop(PROP_LINE_STATES)):
            if state != LINESTATE_NORMAL:
                self.ed.set_prop(PROP_LINE_STATE, (nline, target_state))
