import sublime, sublime_plugin
import re

# ============== auto-folding short if statements for Go

REMOVE_WHITESPACE = re.compile(r"\n\s*")
def find_short_ifs(view, settings):
    folds = []
    cur_pt = 0
    for i in range(1000): # limited in case bugs, could be while True
        if_stmt = view.find(r" +if[ \(](.*)[ \)]\{\n[^\{\}\n]*\n\s*\}", cur_pt)
        if if_stmt is None or if_stmt.empty():
            break # no more found


        # check that if we folded it the line wouldn't be too long
        stmt = view.substr(if_stmt)
        stmt = REMOVE_WHITESPACE.sub(" ", stmt)
        if len(stmt) > settings.get('max_line_length', 100):
            continue

        # print(stmt)

        # find the parts to fold, this is kinda overkill
        sub_pt = if_stmt.begin()
        for i in range(10): # limited in case bugs, could be while True
            line_break = view.find(r"\n\s*", sub_pt)
            if line_break is None or line_break.empty() or line_break.begin() >= if_stmt.end():
                break # no more found
            folds.append(line_break)
            sub_pt = line_break.end()

        # move past this one
        cur_pt = if_stmt.end()

    return folds

class FoldShortIfsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings("stopfmt.sublime-settings")
        folds = find_short_ifs(self.view, settings)
        did_fold = self.view.fold(folds)
        if not did_fold: # already folded, toggle off
            self.view.unfold(folds)

class FoldListener(sublime_plugin.EventListener):
    def on_load(self, view):
        if view.score_selector(0,'source.go') > 0:
            settings = sublime.load_settings("stopfmt.sublime-settings")
            if settings.get('auto_fold_go', False):
                view.run_command('fold_short_ifs')


# ================ folding function bodies

INDENT_RE = re.compile('^\s*')

def line_indent(view, row):
    pt = view.text_point(row,0)
    line = view.full_line(pt)
    content = view.substr(line)
    if len(content) <= 1:
        return 10000 # blank lines have arbitrarily high indent
    start,end = INDENT_RE.match(content).span(0)
    return end-start

def find_function_bodies(view, decls):
    last_row, last_col = view.rowcol(view.size())
    fold_regions = []
    for decl in decls:
        line_region = view.full_line(decl)
        start_row, _ = view.rowcol(decl.a)
        end_row, _ = view.rowcol(decl.b)
        fn_indent = line_indent(view, start_row)

        # find lines until closed indent
        cur_row = end_row+1
        while True:
            if cur_row == last_row:
                break
            indent = line_indent(view, cur_row)
            if indent <= fn_indent:
                break
            cur_row += 1

        # compute region
        if (cur_row - end_row) > 1:
            final_line = view.full_line(view.text_point(cur_row, 0))
            if final_line.size() > 4:
                # for languages like python, or when the end is otherwise long
                # collapse just before the closing bit
                end_pt = view.text_point(cur_row-1,0)
            else:
                final_line_indent = line_indent(view, cur_row)
                end_pt = view.text_point(cur_row, final_line_indent)
            fold_regions.append(sublime.Region(line_region.b-1, end_pt))

    return fold_regions


def find_all_functions(view):
    if view.score_selector(0,'source.rust') > 0:
        fn_bodies = view.find_by_selector('meta.function meta.block')
        folds = [sublime.Region(r.a+1,r.b-1) for r in fn_bodies]
    else:
        fn_decls = view.find_by_selector('meta.function, entity.name.function')
        folds = find_function_bodies(view, fn_decls)
    return folds

class FoldBlockScopesCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        selector = args.get('selector') or 'meta.function meta.block'
        folds = self.view.find_by_selector(selector)
        # print("folding " + len(folds))
        did_fold = self.view.fold(folds)
        if not did_fold: # already folded, toggle off
            self.view.unfold(folds)

class FoldFunctionBodiesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        folds = find_all_functions(self.view)
        # print("folding " + len(folds))
        did_fold = self.view.fold(folds)
        if not did_fold: # already folded, toggle off
            self.view.unfold(folds)
