from minerule.analyze import HostsQuery, Proxies, analyze_rules
from minerule.shellagent import ShellAgent
import base64
import json


def p1(args) -> HostsQuery:
    return HostsQuery(**args)


def p2(args) -> Proxies:
    proxies = Proxies(
        ShellAgent(**args["central_vm"]), ShellAgent(**args["domestic_vm"])
    )
    if "other_vms" in args:
        for k in args["other_vms"]:
            proxies.other_vms[k] = ShellAgent(**args["other_vms"][k])


def handle_event(event, context):
    args = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
    analyze_rules(p1(args["HostsQuery"]), p2(args["Proxies"]), args["ping_count"])
