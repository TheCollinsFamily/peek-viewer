import urllib.request, json, sys, zipfile, io
sys.stdout.reconfigure(encoding='utf-8')

# Get latest run
url = "https://api.github.com/repos/TheCollinsFamily/peek-viewer/actions/runs?per_page=1"
req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
r = urllib.request.urlopen(req)
d = json.loads(r.read())
run_id = d["workflow_runs"][0]["id"]
print("Run ID:", run_id)

# Get jobs
url2 = "https://api.github.com/repos/TheCollinsFamily/peek-viewer/actions/runs/" + str(run_id) + "/jobs"
req2 = urllib.request.Request(url2, headers={"Accept": "application/vnd.github.v3+json"})
r2 = urllib.request.urlopen(req2)
jobs = json.loads(r2.read())

for job in jobs["jobs"]:
    job_id = job["id"]
    print("Job ID:", job_id, "Name:", job["name"])
    
    # Get logs for this job
    log_url = "https://api.github.com/repos/TheCollinsFamily/peek-viewer/actions/jobs/" + str(job_id) + "/logs"
    try:
        log_req = urllib.request.Request(log_url, headers={"Accept": "application/vnd.github.v3+json"})
        log_resp = urllib.request.urlopen(log_req)
        log_text = log_resp.read().decode('utf-8', errors='replace')
        
        # Find the Code sign section
        lines = log_text.split('\n')
        in_codesign = False
        for line in lines:
            if 'Code sign' in line or 'DEBUG' in line or 'ERROR' in line or 'WARNING' in line:
                in_codesign = True
            if in_codesign:
                print(line)
            if in_codesign and ('Notarize' in line or 'List build' in line):
                break
    except Exception as e:
        print("Could not get logs:", e)
        print("(Private repo - need auth token)")
