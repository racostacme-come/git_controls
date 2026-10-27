#!/usr/bin/env python3
"""Generate an offline, interactive Visual Studio 2022 Git guide (Python 3)."""
import argparse
import html
import json
from pathlib import Path
import webbrowser


# Category, command, purpose, Visual Studio route, caution.
COMMANDS = [
    ('Start', 'git clone <url>', 'Download a repository and its history.', 'Start window → Clone a repository; paste the GitHub HTTPS URL.', ''),
    ('Start', 'git init', 'Create a local repository in an existing folder.', 'Git → Create Git Repository. Choose Local only, or GitHub to publish.', ''),
    ('Start', 'git config --global user.name "Your Name"', 'Set the author name for future commits.', 'Git → Settings → Git Global Settings → User Name.', 'This is commit identity, not GitHub authentication.'),
    ('Start', 'git config --global user.email "you@example.com"', 'Set the author email for future commits.', 'Git → Settings → Git Global Settings → User Email.', 'Use your GitHub verified email or your GitHub-provided noreply email.'),
    ('Inspect', 'git status', 'See modified, staged and untracked files.', 'View → Git Changes.', ''),
    ('Inspect', 'git diff', 'Compare unstaged edits with the index.', 'Git Changes → double-click a changed file.', ''),
    ('Inspect', 'git diff --staged', 'Review exactly what the next commit includes.', 'Git Changes → Staged Changes → double-click a file.', ''),
    ('Inspect', 'git log --oneline --graph --all', 'Explore commits and branch relationships.', 'Git → Manage Branches → Git Repository window; select a branch to see history.', ''),
    ('Inspect', 'git show <commit>', 'Inspect one commit and its patch.', 'Git Repository → double-click a commit.', ''),
    ('Inspect', 'git blame <file>', 'Find the last commit that changed each line.', 'Solution Explorer → right-click file → Git → Blame (where available); otherwise use Terminal.', ''),
    ('Save', 'git add <file>', 'Stage selected file content for a commit.', 'Git Changes → + beside a file, or Stage All (+).', 'Review files first. Do not stage credentials, build outputs or unrelated changes.'),
    ('Save', 'git restore --staged <file>', 'Unstage a file while keeping its edits.', 'Git Changes → Staged Changes → Unstage (−).', ''),
    ('Save', 'git commit -m "Describe the change"', 'Save staged changes as a local commit.', 'Git Changes → enter a message → Commit Staged.', 'Commit All can include unstaged tracked edits. Commit does not upload to GitHub.'),
    ('Save', 'git commit --amend', 'Replace the latest local commit with an updated commit.', 'Git Changes → commit options → Amend (if exposed); otherwise Terminal.', 'Rewrites history. Avoid amending commits others already use.'),
    ('Branch', 'git branch', 'List local branches.', 'Git → Manage Branches, or branch selector on the status bar.', ''),
    ('Branch', 'git switch -c feature/my-change', 'Create and switch to a feature branch.', 'Git → New Branch → enter name → check Checkout branch.', ''),
    ('Branch', 'git switch <branch>', 'Switch to an existing branch.', 'Status bar branch selector → select branch.', 'Commit or stash edits before switching if they would conflict.'),
    ('Branch', 'git branch -d <branch>', 'Delete a merged local branch.', 'Git Repository → right-click a local branch → Delete.', 'Switch away first. -D forces deletion and can lose the branch reference to unmerged work.'),
    ('Branch', 'git merge <branch>', 'Bring another branch into the current branch.', 'Check out the destination; Git Repository → right-click source branch → Merge into Current Branch.', 'Resolve conflicts, review and test before pushing.'),
    ('Branch', 'git rebase <branch>', 'Replay current branch commits on a new base.', 'Git Repository → right-click target → Rebase Current Branch onto (where available).', 'Rewrites commit IDs. Use for your own unpublished commits unless your team explicitly agrees.'),
    ('Branch', 'git cherry-pick <commit>', 'Apply one existing commit to the current branch.', 'Git Repository history → right-click commit → Cherry-Pick.', 'Can conflict or duplicate a change already present.'),
    ('GitHub', 'git remote -v', 'Inspect fetch and push destinations.', 'Git → Settings → Git Repository Settings → Remotes.', 'Check the destination before publishing private code.'),
    ('GitHub', 'git remote add origin <url>', 'Connect a local repository to an existing GitHub repository.', 'Git Repository Settings → Remotes → Add. For a new GitHub repository, use Git → Create Git Repository.', 'Do not overwrite an existing origin blindly. Create the GitHub repository first when using Terminal.'),
    ('GitHub', 'git fetch origin', 'Download remote commits without changing your files.', 'Git → Fetch, or Fetch in Git Changes.', ''),
    ('GitHub', 'git pull --ff-only', 'Update the current branch only if a fast-forward is possible.', 'Use View → Terminal for this exact option. Git → Pull follows configured merge/rebase behavior.', 'If branches diverged, inspect history and deliberately merge or rebase; do not force the update.'),
    ('GitHub', 'git push -u origin <branch>', 'Upload a branch and configure its upstream on the first push.', 'Git Changes → Push; a new local branch may show Publish Branch.', 'Authenticate with your GitHub account through Visual Studio. Never paste tokens into source files.'),
    ('GitHub', 'git push', 'Upload new commits to the configured upstream.', 'Git → Push, or the up arrow in Git Changes.', 'A push does not upload uncommitted files. Rejected push: fetch, inspect, integrate, test, then push again.'),
    ('GitHub', 'git push origin --delete <branch>', 'Delete a branch on GitHub.', 'GitHub repository → Branches → delete a merged branch; or Terminal.', 'Shared remote action: confirm the branch is no longer needed.'),
    ('GitHub', 'git tag -a v1.0.0 -m "Version 1.0.0"', 'Mark a commit with an annotated release tag.', 'Git Repository history → right-click commit → New Tag (where available); otherwise Terminal.', ''),
    ('GitHub', 'git push origin v1.0.0', 'Publish one chosen tag.', 'Terminal; confirm the tag appears on GitHub.', 'Ordinary branch push does not necessarily publish tags.'),
    ('Recover', 'git stash push -u -m "Work in progress"', 'Temporarily shelve tracked and untracked work.', 'Git Changes → stash options → Stash All; use Terminal for the exact -u behavior.', 'Ignored files are not included by -u. A stash is local, not a GitHub backup.'),
    ('Recover', 'git stash list', 'List saved stashes.', 'Git Repository → Stashes (when available), or Terminal.', ''),
    ('Recover', 'git stash apply', 'Restore a stash while retaining its backup entry.', 'Git Repository → Stashes → right-click → Apply, or Terminal.', 'Can conflict. Review before dropping the stash. pop removes it after a successful apply.'),
    ('Recover', 'git revert <commit>', 'Create a new commit that reverses an earlier commit.', 'Git Repository history → right-click commit → Revert.', 'Usually preferable to rewriting published history. A merge commit needs deliberate parent selection.'),
    ('Recover', 'git restore <file>', 'Discard unstaged changes in a tracked file.', 'Git Changes → right-click file → Undo Changes.', 'Destructive: uncommitted edits may be unrecoverable. Stash or copy them first.'),
    ('Recover', 'git reset --soft HEAD~1', 'Undo the latest commit while leaving its changes staged.', 'Use Terminal for the exact soft mode.', 'Rewrites local history; avoid on shared published commits.'),
    ('Recover', 'git reset --hard <commit>', 'Reset tracked files and the index to a commit.', 'Use Terminal only after deliberate review.', 'Destructive: discards tracked edits and can remove obstructing untracked paths. Commit/stash/copy first.'),
    ('Recover', 'git clean -nd', 'Preview untracked files and directories that clean would remove.', 'Terminal.', 'git clean -fd performs deletion. Review the preview and back up files first; Git cannot recover untracked content.'),
    ('Recover', 'git reflog', 'Find recent local branch/HEAD movements for recovery.', 'Terminal; inspect entries before creating a recovery branch.', 'Recovery is local and time limited. It does not recover arbitrary uncommitted edits.'),
    ('Conflicts', 'git merge --abort', 'Abandon an in-progress merge.', 'Terminal, or Abort Merge if offered by the current Visual Studio version.', 'Start merges from a clean working tree so prior edits are easier to preserve.'),
    ('Conflicts', 'git rebase --continue', 'Continue a rebase after resolving and staging conflicts.', 'Resolve files in the merge editor, stage them, then use Terminal.', 'Use git rebase --abort to return to the pre-rebase state.'),
    ('Advanced', 'git ls-files', 'List files tracked in the index.', 'Terminal.', ''),
    ('Advanced', 'git ls-remote origin', 'Inspect remote refs without updating your working tree.', 'Terminal.', ''),
    ('Advanced', 'git bisect start', 'Find a regression by testing commits with git bisect good / bad.', 'Terminal. Mark a known bad and known good commit; test each selected commit; finish with git bisect reset.', 'Use a clean working tree. Each good/bad decision must reflect an actual test.'),
    ('Advanced', 'git submodule update --init --recursive', 'Initialize the submodules recorded by the repository.', 'Terminal in the parent repository.', 'Submodules are separate repositories; check their remotes and commit/push changes separately.'),
    ('Advanced', 'git help -a', 'List the Git commands available in your installed version.', 'View → Terminal → Developer PowerShell, then run the command.', 'This guide covers common and selected advanced commands, not every Git plumbing command. Use git help <command> for complete options.'),
]

TEMPLATE = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Git → GitHub | Visual Studio 2022</title>
<style>
:root{color-scheme:dark;font:16px/1.6 system-ui;background:#0b1220;color:#e2e8f0}body{max-width:1150px;margin:auto;padding:24px}h1{font-size:clamp(28px,5vw,46px);line-height:1.15}h2{line-height:1.3}p{color:#bac8dd}section,.card{background:#141f32;border:1px solid #334155;border-radius:14px;padding:22px;margin:18px 0}button,input,select{font:inherit;padding:10px 14px;border:1px solid #64748b;border-radius:8px;background:#1e304b;color:#fff}button{cursor:pointer}button:hover,button:focus-visible{background:#304d75}button:disabled{opacity:.4;cursor:default}input{flex:1;min-width:180px}nav,.toolbar,.actions{display:flex;gap:10px;flex-wrap:wrap}nav a,a{color:#93c5fd}code{overflow-wrap:anywhere;color:#8ee5cb}pre{white-space:pre-wrap}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}.card{margin:0}.card h3{margin-top:0}.warning{color:#fcd28b;border-left:3px solid #f4b860;padding-left:12px}.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.node{background:#0b1220;padding:16px;border:1px solid #526b8d;border-radius:10px}.count{display:block;font-size:28px;color:#8ee5cb}#message{min-height:3em}small{color:#b8c4d8}summary{cursor:pointer;font-weight:600}li{margin:10px 0}@media(max-width:650px){.flow{grid-template-columns:1fr 1fr}body{padding:14px}}
</style>
<header><small>OFFLINE INTERACTIVE FIELD GUIDE</small><h1>Your code. Your commits.<br>Your GitHub.</h1><p>Learn Git in Visual Studio 2022: inspect → stage → commit → fetch → integrate → push.</p><nav><a href="#simulator">Try the workflow</a><a href="#sync">Synchronize with GitHub</a><a href="#reference">Command reference</a><a href="#conflicts">Fix conflicts</a></nav></header>
<section><strong>Before you begin</strong><p>Install Visual Studio 2022 with your project’s workload (for this repository: Desktop development with C++). Open the solution, then View → Git Changes and Git → Manage Branches. Sign in to your GitHub account when Visual Studio requests it. Menu wording varies by VS 2022 update and settings; use View → Terminal for commands without a UI equivalent. Replace angle-bracket placeholders before running commands.</p><p>This page simulates Git; it never reads your repository, executes commands, or uploads files. GitHub pull requests and branch protection are hosting features, not Git commands.</p></section>
<section id="simulator"><h2>1. Try the local → GitHub workflow</h2><p>One simulated file, one branch and one remote. Commit IDs and branches are simplified; real Git stores snapshots, and staging captures a file’s content at that moment.</p><div class="flow"><div class="node">Working files<span class="count" id="work">0</span>unstaged edits</div><div class="node">Staging area<span class="count" id="stage">0</span>staged edits</div><div class="node">Local history<span class="count" id="local">0</span>your commits</div><div class="node">GitHub<span class="count" id="remote">0</span>your uploaded commits</div></div><div class="actions" style="margin-top:18px"><button data-action="edit">Edit file</button><button data-action="stage">Stage</button><button data-action="commit">Commit</button><button data-action="push">Push</button><button data-action="teammate">Teammate pushes</button><button data-action="fetch">Fetch</button><button data-action="pull">Integrate / Pull</button><button data-action="reset">Restart simulation</button></div><p id="message" role="status" aria-live="polite">Start by editing a file.</p><small id="tracking"></small></section>
<section id="sync"><h2>2. Synchronize changes with GitHub</h2><ol><li><strong>Clone or publish.</strong> For an existing GitHub repo: Git → Clone Repository. For a local project: Git → Create Git Repository → GitHub → choose owner, name and visibility → Create and Push. If origin already exists, inspect it instead of creating another remote.</li><li><strong>Start a branch.</strong> Fetch and update your base branch, then Git → New Branch. This repository currently uses <code>master</code>; other repositories often use <code>main</code>. Use the actual branch name.</li><li><strong>Edit, review, stage and commit.</strong> In Git Changes, inspect diffs, stage intended files and choose Commit Staged with a useful message. Secrets belong outside Git; .gitignore does not untrack files already committed.</li><li><strong>Fetch and inspect.</strong> Fetch downloads remote history without changing your files. Pull integrates it into your current branch. In Terminal, <code>git pull --ff-only</code> refuses divergent histories; if that happens, inspect the graph and deliberately merge or rebase according to your team’s policy.</li><li><strong>Integrate and test.</strong> Resolve any conflicts, finish the merge/rebase and run your project’s build and tests. This repository currently has a pre-existing C++ compilation error at line 8; synchronization does not fix that code defect.</li><li><strong>Push / Publish Branch.</strong> First CLI push: <code>git push -u origin &lt;branch&gt;</code>. Later: <code>git push</code>. Visual Studio may offer Sync (pull then push); review incoming work first. Push sends commits, not unsaved or uncommitted edits.</li><li><strong>Open a pull request on GitHub.</strong> Select your feature branch → Compare &amp; pull request → choose the correct base → review diff → Create pull request. Follow reviews, checks and branch protection; merge only when authorized. Then fetch/pull the base branch locally. A pull request is separate from git pull.</li></ol><details><summary>Push rejected or authentication failed?</summary><p>For non-fast-forward rejection, fetch and inspect incoming commits, integrate them, resolve conflicts and test before pushing. Do not use force push as a shortcut. For protected branches, push a feature branch and open a pull request. For authentication, check the remote URL, Visual Studio’s signed-in account, repository permission and organization SSO authorization. GitHub account passwords are not accepted for HTTPS Git operations; use the supported sign-in/credential manager flow. Never share a token in chat or commit it.</p></details></section>
<section id="reference"><h2>3. Search the command reference</h2><p>Common workflows and selected advanced commands. For the complete command list installed on your machine use <code>git help -a</code>; for every option use <code>git help &lt;command&gt;</code>.</p><div class="toolbar"><input id="search" type="search" aria-label="Search Git commands" placeholder="Search: push, undo, branch, conflicts…"><select id="category" aria-label="Command category"><option value="">All categories</option>__OPTIONS__</select></div><p id="results" role="status"></p><div id="cards"></div></section>
<section id="conflicts"><h2>4. Resolve a merge conflict</h2><ol><li>Git Changes lists unmerged files. Open a conflicted file in Visual Studio’s merge editor.</li><li>Inspect Current (your checked-out branch), Incoming and Result. Choose or edit the intended result; accepting both is not always correct.</li><li>Remove conflict markers and verify the combined behavior. Save and stage resolved files (<code>git add &lt;file&gt;</code>).</li><li>For a merge, complete its commit. For a rebase, run <code>git rebase --continue</code>; repeat if another commit conflicts. Abort with <code>git merge --abort</code> or <code>git rebase --abort</code> if you need to reconsider.</li><li>Build and test, inspect history, then push. Coordinate with teammates before rewriting any published history.</li></ol></section>
<footer><p>Official references: <a href="https://learn.microsoft.com/en-us/visualstudio/version-control/git-with-visual-studio?view=vs-2022">Visual Studio Git documentation</a> · <a href="https://git-scm.com/docs">Git manual</a> · <a href="https://docs.github.com/en/pull-requests">GitHub pull requests</a>. The guide itself works offline; these links require internet.</p></footer>
<script>
'use strict';
const commands = __DATA__;
const $ = id => document.getElementById(id);
function render(){
 const query=$('search').value.toLowerCase(), category=$('category').value;
 const matches=commands.filter(row=>(!category||row[0]===category)&&row.join(' ').toLowerCase().includes(query));
 $('cards').replaceChildren();
 matches.forEach(([group,command,purpose,route,caution])=>{
  const card=document.createElement('article');card.className='card';
  const label=document.createElement('small');label.textContent=group;
  const title=document.createElement('h3'),code=document.createElement('code');code.textContent=command;title.append(code);
  const desc=document.createElement('p');desc.textContent=purpose;
  const ui=document.createElement('p');ui.textContent='Visual Studio: '+route;
  card.append(label,title,desc,ui);
  if(caution){const warning=document.createElement('p');warning.className='warning';warning.textContent=caution;card.append(warning);}
  const copy=document.createElement('button');copy.textContent='Copy command';copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(command);copy.textContent='Copied';}catch{copy.textContent='Select the command above to copy';}});card.append(copy);$('cards').append(card);
 });
 $('results').textContent=matches.length+' of '+commands.length+' commands';
}
$('search').addEventListener('input',render);$('category').addEventListener('change',render);render();
let state;
function reset(){state={work:0,stage:0,local:0,remote:0,team:0,known:0,integrated:0};}
function action(name){let msg='';switch(name){
 case 'edit':state.work++;msg='File edited. Review the diff, then stage the content you want to commit.';break;
 case 'stage':if(!state.work){msg='No unstaged edits. Edit a file first.';break;}state.stage+=state.work;state.work=0;msg='Edits staged. A later edit stays unstaged until you stage again.';break;
 case 'commit':if(!state.stage){msg='Nothing staged. Stage an edit first.';break;}state.local++;state.stage=0;msg='Local commit created. GitHub has not changed.';break;
 case 'teammate':state.team++;msg='A teammate pushed. Your local remote-tracking information is stale until you fetch.';break;
 case 'fetch':state.known=state.team;msg='Fetched remote history. Your working files and local commits are unchanged.';break;
 case 'pull':if(state.work||state.stage){msg='Commit or stash your edits before integrating in this tutorial.';break;}state.known=state.team;if(state.integrated===state.team){msg='No incoming commits to integrate.';break;}msg=state.local>state.remote?'Histories diverged. Simulation: you deliberately merge incoming commits and resolve any conflicts. A real --ff-only pull would refuse this.':'Incoming history fast-forwarded locally.';state.integrated=state.team;break;
 case 'push':if(state.team>state.integrated){msg='Push rejected: incoming commits are missing locally. Fetch, inspect, then integrate and test.';break;}if(state.remote===state.local){msg='No new commits to upload. Uncommitted edits stay local.';break;}state.remote=state.local;msg='Your commits are now on GitHub. Open a pull request if your team uses reviews.';break;
 case 'reset':reset();msg='Simulation restarted. Start by editing a file.';break;
 }['work','stage','local','remote'].forEach(key=>$(key).textContent=state[key]);$('tracking').textContent=`Teammate commits on GitHub: ${state.team} · Known after fetch: ${state.known} · Integrated locally: ${state.integrated}`;$('message').textContent=msg;
}
reset();action('reset');document.querySelectorAll('[data-action]').forEach(button=>button.addEventListener('click',()=>action(button.dataset.action)));
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('git-guide.html'))
    parser.add_argument('--open', action='store_true', help='Open the generated file in your browser')
    args = parser.parse_args()
    options = ''.join(f'<option>{html.escape(category)}</option>'
                      for category in dict.fromkeys(row[0] for row in COMMANDS))
    data = json.dumps(COMMANDS).replace('<', r'\u003c')
    page = TEMPLATE.replace('__OPTIONS__', options).replace('__DATA__', data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding='utf-8')
    print(f'Created {args.output.resolve()} ({len(COMMANDS)} command cards)')
    if args.open:
        webbrowser.open(args.output.resolve().as_uri())


if __name__ == '__main__':
    main()
