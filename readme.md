# Git-Garden

## Common Test Cases

```
python garden.py
python garden.py --no-fetch --no-prune --remote
python garden.py --no-fetch --no-prune --ff --delete --quiet

git switch -c temp # local only
git switch -c temp2; git push -f; git push origin --delete temp2 # gone
git switch -c temp3; git commit -m "Temp" --allow-empty; git push -f; git reset HEAD~ --hard # behind
git switch -c temp4; git push -f; git push origin --delete temp4; git reset HEAD~ --soft # uncommitted changes

git switch git-garden -f; git branch -D temp temp2 temp3 temp4 # cleanup
git push origin --delete temp temp2 temp3 temp4 # cleanup
```