import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

url = "https://api.github.com/repos/TheCollinsFamily/peek-viewer/actions/runs?per_page=1"
req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
r = urllib.request.urlopen(req)
d = json.loads(r.read())
run = d["workflow_runs"][0]
run_id = run["id"]
print("Run: " + str(run['name']))
print("Status: " + str(run['status']))
print("Conclusion: " + str(run['conclusion']))

url2 = "https://api.github.com/repos/TheCollinsFamily/peek-viewer/actions/runs/" + str(run_id) + "/jobs"
req2 = urllib.request.Request(url2, headers={"Accept": "application/vnd.github.v3+json"})
r2 = urllib.request.urlopen(req2)
jobs = json.loads(r2.read())
for job in jobs["jobs"]:
    print("\nJob: " + job['name'] + " - " + str(job['status']) + " / " + str(job['conclusion']))
    for step in job["steps"]:
        if step["conclusion"] == "success":
            icon = "OK"
        elif step["conclusion"] == "failure":
            icon = "FAIL"
        elif step["status"] == "in_progress":
            icon = "..."
        else:
            icon = "-"
        print("  [" + icon + "] " + step['name'])
