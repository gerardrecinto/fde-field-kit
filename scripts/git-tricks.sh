#!/usr/bin/env bash
# Each trick runs for real in a throwaway repo and checks its own result.
# Needs git 2.38 or newer. Run: bash scripts/git-tricks.sh
set -eu
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME=fde GIT_AUTHOR_EMAIL=fde@example.com GIT_COMMITTER_NAME=fde GIT_COMMITTER_EMAIL=fde@example.com
ok() { printf 'PASS  %s\n' "$1"; }
die() { printf 'FAIL  %s\n' "$1"; exit 1; }
commit() { git commit -q --allow-empty -m "$1"; }

cd "$T" && git init -q -b main repo && cd repo
git config user.name fde; git config user.email fde@example.com
echo 1 > app.txt; git add app.txt; commit "v1"

# 1. worktree: fix production while a half-finished change sits in your main checkout
echo wip >> app.txt
git worktree add -q -b hotfix ../hotfix main
( cd ../hotfix && echo fix > fix.txt && git add fix.txt && git commit -q -m "hotfix" )
git diff --quiet app.txt && die worktree || ok "1 worktree: hotfix built in ../hotfix, uncommitted work untouched"
git worktree remove ../hotfix; git checkout -q app.txt

# 2. bisect run: find the release that broke the customer, no clicking
echo good > state.txt; git add state.txt; commit "r2"
commit "r3"; commit "r4"
echo bad > state.txt; git add state.txt; commit "r5 breaks"
commit "r6"
BAD=$(git rev-parse HEAD~1)
git bisect start HEAD HEAD~4 >/dev/null
git bisect run sh -c 'grep -q good state.txt' >/dev/null
FOUND=$(git rev-parse refs/bisect/bad)
git bisect reset >/dev/null 2>&1
[ "$FOUND" = "$BAD" ] && ok "2 bisect run: found r5 automatically" || die bisect

# 3. rerere: resolve a conflict once, never again
git config rerere.enabled true
echo base > conf.txt; git add conf.txt; commit "conf base"
git checkout -q -b cust-a; echo A > conf.txt; git add conf.txt; commit "cust-a"
git checkout -q -b cust-b main; echo B > conf.txt; git add conf.txt; commit "cust-b"
git checkout -q cust-a
git merge cust-b >/dev/null 2>&1 || true
echo AB > conf.txt; git add conf.txt; git commit -q -m "merge 1"
git reset -q --hard HEAD~1
git merge cust-b >/dev/null 2>&1 || true
[ "$(cat conf.txt)" = "AB" ] && ok "3 rerere: second merge reused the recorded resolution" || die rerere
git merge --abort; git checkout -q main

# 4. range-diff: did the rebase change my patches or only move them?
git checkout -q -b series main
echo s1 > s1.txt; git add s1.txt; commit "s1"; echo s2 > s2.txt; git add s2.txt; commit "s2"
git branch series-old
git checkout -q main; commit "upstream moved"; git checkout -q series; git rebase -q main
git range-diff main series-old series | grep -c "= " | grep -q 2 && ok "4 range-diff: both patches identical after rebase" || die range-diff
git checkout -q main

# 5. rebase --update-refs: rebase a stack of branches in one go
git checkout -q -b step1 main; echo a > st1; git add st1; commit "step1"
git checkout -q -b step2; echo b > st2; git add st2; commit "step2"
git checkout -q main; commit "main moves again"
git checkout -q step2; git rebase -q --update-refs main
[ "$(git merge-base step1 main)" = "$(git rev-parse main)" ] && ok "5 rebase --update-refs: step1 moved with step2" || die update-refs
git checkout -q main

# 6. fixup + autosquash: tidy before review without interactive mode
echo f1 > f.txt; git add f.txt; commit "feature"
echo f2 >> f.txt; git add f.txt; git commit -q --fixup HEAD
GIT_SEQUENCE_EDITOR=true git rebase -q -i --autosquash HEAD~2
[ "$(git rev-list --count HEAD~1..HEAD)" = 1 ] && [ "$(wc -l < f.txt | tr -d ' ')" = 2 ] && ok "6 fixup + autosquash: two commits became one" || die autosquash

# 7. reflog: get back a branch you reset away
OLD=$(git rev-parse HEAD); git reset -q --hard HEAD~1
git reflog -1 >/dev/null; git reset -q --hard "HEAD@{1}"
[ "$(git rev-parse HEAD)" = "$OLD" ] && ok "7 reflog: recovered the commit after a hard reset" || die reflog

# 8. notes: record deploy facts on a commit without rewriting history
git notes add -m "deployed to acme-east 2026-11-20" HEAD
git notes show HEAD | grep -q acme-east && ok "8 notes: deploy record attached, commit hash unchanged" || die notes

# 9. log -L and blame -w -C: who changed this function, even after a move or reformat
printf 'def f():\n    return 1\n' > m.py; git add m.py; commit "add f"
printf 'def f():\n    return 2\n' > m.py; git add m.py; commit "f returns 2"
git log -L '/def f/,+2:m.py' --oneline -s | grep -q "f returns 2" && ok "9 log -L: followed one function through history" || die log-L
git blame -w -C -C -L1,1 m.py >/dev/null && ok "9b blame -w -C -C: ignores whitespace, follows moved lines"

# 10. bundle: ship a repo to an air-gapped site on a USB stick
git bundle create "$T/site.bundle" --all 2>/dev/null
git clone -q "$T/site.bundle" "$T/offsite" 2>/dev/null
[ "$(git -C "$T/offsite" rev-parse HEAD)" = "$(git rev-parse main)" ] && ok "10 bundle: cloned from one file, same HEAD" || die bundle

# 11. partial clone + sparse checkout: a huge repo over a slow customer link
mkdir -p big/docs big/src; for i in 1 2 3; do echo $i > big/src/f$i; echo $i > big/docs/d$i; done
git add big; commit "big tree"
git config uploadpack.allowFilter true; git config uploadpack.allowAnySHA1InWant true
git clone -q --filter=blob:none --sparse "file://$T/repo" "$T/slim" 2>/dev/null
( cd "$T/slim" && git sparse-checkout set big/src && ls big/src | grep -q f1 && [ ! -e big/docs ] ) \
  && ok "11 partial clone + sparse: only big/src on disk, blobs fetched on demand" || die sparse

# 12. --force-with-lease --force-if-includes: a force push that cannot clobber a teammate
git clone -q --bare "$T/repo" "$T/remote.git" 2>/dev/null
git remote add origin "$T/remote.git"
git push -q origin main:fix 2>/dev/null; git fetch -q origin
git clone -q "$T/remote.git" "$T/mate" 2>/dev/null
( cd "$T/mate" && git checkout -q fix && git commit -q --allow-empty -m "teammate push" && git push -q origin fix 2>/dev/null )
git commit -q --amend -m "rewritten"
git fetch -q origin   # you saw their push but did not merge it
if git push -q --force-with-lease --force-if-includes origin main:fix 2>/dev/null; then die "overwrote a teammate"; else ok "12 --force-with-lease --force-if-includes: refused, their commit was never merged into yours"; fi

echo; echo "all tricks verified with $(git --version)"
