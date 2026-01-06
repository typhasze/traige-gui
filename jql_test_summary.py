#!/usr/bin/env python3
"""
JIRA Issues Analyzer - Optimized version for pattern-based grouping with vehicle analysis.
"""

import csv
import os
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime

from jira import JIRA

# Configuration
CONFIG = {
    "server": "https://ventitechnologies.atlassian.net",
    "auth": (os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", "")),
    "base_jql": "project = BUG AND type = Bug AND labels = psa_driverless",
    "order": "ORDER BY cf[10052] ASC, cf[10312] ASC, summary ASC, cf[10084] ASC, created DESC",
}

QUERIES = {
    "Non-Operational": (
        '"intervention type[dropdown]" = "Direct Intervention" AND '
        '"issue criticality[dropdown]" IN (Critical, "P1 Critical", Non-Critical) '
        "AND status NOT IN (Invalid)"
    ),
    "Operational": (
        '"intervention type[dropdown]" = "Direct Intervention" AND '
        '"issue criticality[dropdown]" IN (Operational) '
        "AND status NOT IN (Invalid)"
    ),
    "E-Stop": 'summary ~ "e_stop"',
}


def get_date_range():
    """Get and validate date range from user."""
    while True:
        try:
            start = input("Start date (YYYY-MM-DD): ").strip()
            end = input("End date (YYYY-MM-DD): ").strip()

            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")

            if start_dt >= end_dt:
                print("❌ Start date must be before end date.")
                continue

            return start, end
        except ValueError:
            print("❌ Invalid format. Use YYYY-MM-DD")
        except KeyboardInterrupt:
            print("\n❌ Cancelled.")
            sys.exit(0)


def build_queries(start_date, end_date):
    """Build all JQL queries with URLs."""
    queries = {}
    for name, condition in QUERIES.items():
        jql = f"""{CONFIG['base_jql']} AND "date and time[time stamp]" >= "{start_date} 07:30"
                  AND "date and time[time stamp]" < "{end_date} 07:30" AND {condition} {CONFIG['order']}"""

        queries[name] = {"jql": jql, "url": f"{CONFIG['server']}/issues/?jql={urllib.parse.quote(jql)}"}
    return queries


def connect_jira():
    """Connect to JIRA."""
    try:
        return JIRA(server=CONFIG["server"], basic_auth=CONFIG["auth"])
    except Exception as e:
        print(f"❌ JIRA connection failed: {e}")
        sys.exit(1)


def extract_info(summary):
    """Extract pattern and vehicle from summary - optimized version."""
    # Try PSA pattern first (most common)
    if match := re.match(r"^(.*?)\s+PSA(\d+)", summary):
        return match.group(1).strip(), f"PSA{match.group(2)}"

    # Try error codes
    if match := re.match(r"^(Err:\d+|[A-Za-z]+:\d+)", summary):
        return match.group(1), "Unknown"

    # Fallback
    fallback = re.match(r"^([^,\(]{1,50})", summary)
    return (fallback.group(1).strip() if fallback else summary[:50]), "Unknown"


def process_issues(issues):
    """Process and group issues efficiently."""
    patterns = defaultdict(list)
    vehicle_counts = defaultdict(Counter)

    for issue in issues:
        pattern, vehicle = extract_info(issue.fields.summary)
        assignee = getattr(issue.fields.assignee, "displayName", "Unassigned")

        vehicle_counts[pattern][vehicle] += 1
        patterns[pattern].append(
            {
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": assignee,
                "vehicle": vehicle,
            }
        )

    return {
        pattern: {
            "issues": issue_list,
            "vehicle_count": dict(vehicle_counts[pattern]),
            "total_count": sum(vehicle_counts[pattern].values()),
        }
        for pattern, issue_list in patterns.items()
    }


def format_vehicle_stats(vehicle_counts):
    """Format vehicle statistics efficiently."""
    if not vehicle_counts:
        return "0 vehicles"

    total = sum(vehicle_counts.values())
    vehicles = [
        f"{v.replace('PSA', '') if v.startswith('PSA') else v} ({c})" for v, c in sorted(vehicle_counts.items())
    ]
    return f"{total} vehicles: {', '.join(vehicles)}"


def export_to_csv(all_results, start_date, end_date):
    """Export results to CSV efficiently."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jira_issues_{start_date}_{end_date}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, ["Query_Type", "Pattern", "Vehicle_Stats", "Issue_Key", "Vehicle", "Summary", "Status", "Assignee"]
        )
        writer.writeheader()

        for query_type, data in all_results.items():
            # Header
            writer.writerow(
                {"Query_Type": f"{query_type.upper()} ISSUES", "Pattern": f"Total: {data['total_count']} issues"}
            )
            writer.writerow({"Query_Type": "Query Link:", "Pattern": data.get("query_url", "")})
            writer.writerow({})

            # Data
            for pattern, pattern_data in data["grouped_issues"].items():
                vehicle_stats = format_vehicle_stats(pattern_data["vehicle_count"])
                for i, issue in enumerate(pattern_data["issues"]):
                    writer.writerow(
                        {
                            "Query_Type": query_type if i == 0 else "",
                            "Pattern": pattern if i == 0 else "",
                            "Vehicle_Stats": vehicle_stats if i == 0 else "",
                            "Issue_Key": f"{CONFIG['server']}/browse/{issue['key']}",
                            "Vehicle": issue["vehicle"],
                            "Summary": issue["summary"],
                            "Status": issue["status"],
                            "Assignee": issue["assignee"],
                        }
                    )
                writer.writerow({})

    return filename


def export_to_text(all_results, start_date, end_date):
    """Export results to a summary text file in the requested format."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jira_issue_titles_and_links_{start_date}_{end_date}_{timestamp}.txt"
    lines = []
    for query_type, data in all_results.items():
        for pattern, pattern_data in data["grouped_issues"].items():
            # Title line: pattern - vehicle stats
            vehicle_counts = pattern_data["vehicle_count"]
            vehicle_stats = []
            for v, c in sorted(vehicle_counts.items()):
                v_num = v.replace("PSA", "") if v.startswith("PSA") else v
                vehicle_stats.append(f"{v_num} ({c})")
            title_line = f"{pattern} – {', '.join(vehicle_stats)}\n"
            lines.append(title_line)
            # Ticket links
            for issue in pattern_data["issues"]:
                lines.append(f"{CONFIG['server']}/browse/{issue['key']}\n")
            lines.append("\n")
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return filename


def display_results(grouped_issues, query_type=""):
    """Display results to console."""
    if query_type:
        print(f"\n📋 {query_type} Results:")

    for pattern, data in grouped_issues.items():
        issues = data["issues"]
        vehicle_stats = format_vehicle_stats(data["vehicle_count"])

        print(f"\n📊 {pattern} ({len(issues)} issues):")
        print(f"   🚗 {vehicle_stats}")

        for issue in issues:
            print(
                f"  - {issue['key']} ({issue['vehicle']}): {issue['summary']} "
                f"(Status: {issue['status']}, Assignee: {issue['assignee']}) - "
                f"{CONFIG['server']}/browse/{issue['key']}"
            )


def main():
    """Main execution - optimized workflow."""
    print("📅 JIRA Issues Analyzer")
    start_date, end_date = get_date_range()
    print(f"✅ Date range: {start_date} to {end_date}")

    # Connect and build queries
    print("🔗 Connecting to JIRA...")
    jira = connect_jira()
    queries = build_queries(start_date, end_date)

    results = {}

    # Execute queries
    for name, query in queries.items():
        print(f"\n🔍 {name} query...")
        print(f"🔗 {query['url']}")

        try:
            issues = jira.search_issues(query["jql"], maxResults=False)
            count = len(issues)
            print(f"✅ Found {count} issues")

            if count > 0:
                grouped = process_issues(issues)
                results[name] = {"grouped_issues": grouped, "total_count": count, "query_url": query["url"]}
                display_results(grouped, name)
            else:
                results[name] = {"grouped_issues": {}, "total_count": 0, "query_url": query["url"]}

        except Exception as e:
            print(f"❌ Failed: {e}")
            results[name] = {"grouped_issues": {}, "total_count": 0, "query_url": query["url"]}

    # Export and summarize
    if any(r["total_count"] > 0 for r in results.values()):
        csv_filename = export_to_csv(results, start_date, end_date)
        print(f"\n✅ Exported CSV: {csv_filename}")
        txt_filename = export_to_text(results, start_date, end_date)
        print(f"✅ Exported TXT: {txt_filename}")
        total = sum(r["total_count"] for r in results.values())
        print("\n📊 Summary:")
        for name, result in results.items():
            print(f"  {name}: {result['total_count']} issues")
        print(f"  Total: {total} issues")
    else:
        print("\n❌ No issues found.")


if __name__ == "__main__":
    main()
