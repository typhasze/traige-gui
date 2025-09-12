#!/usr/bin/env python3
"""
JIRA Issues Analyzer - Optimized version for pattern-based grouping with vehicle analysis.
"""

from jira import JIRA
from collections import defaultdict, Counter
import re
import csv
from datetime import datetime
import sys
import urllib.parse

# Configuration
CONFIG = {
    'server': 'https://ventitechnologies.atlassian.net',
    'auth': ('hafiz.kosno@ventitechnologies.com', 'ATATT3xFfGF0NH9UwB1voANOi6euu8tpV3zfH-CM9S2wzQjF7LJO0HHG4z1qmaNCUKRz9Vt4DuBROnhp2vgwfux4Fjl9Dj0ADwd6HDxLvZUYS_EB1dtDroUC2zQaWBcVxzOxp8kUlrCvr9iododlYnu999OA8n9OSR6XTLexiC4bkdenRqA2QDc=CFD797F7'),
    'base_jql': 'project = BUG AND type = Bug AND labels = psa_driverless',
    'order': 'ORDER BY cf[10052] ASC, cf[10312] ASC, summary ASC, cf[10084] ASC, created DESC'
}

QUERIES = {
    'Non-Operational': '"intervention type[dropdown]" = "Direct Intervention" AND "issue criticality[dropdown]" IN (Critical, "P1 Critical", Non-Critical) AND status NOT IN (Invalid)',
    'Operational': '"intervention type[dropdown]" = "Direct Intervention" AND "issue criticality[dropdown]" IN (Operational) AND status NOT IN (Invalid)',
    'E-Stop': 'summary ~ "e_stop"'
}

def get_date_range():
    """Get and validate date range from user."""
    while True:
        try:
            start = input("Start date (YYYY-MM-DD): ").strip()
            end = input("End date (YYYY-MM-DD): ").strip()
            
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            
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
        jql = f'''{CONFIG['base_jql']} AND "date and time[time stamp]" >= "{start_date} 07:30" 
                  AND "date and time[time stamp]" < "{end_date} 07:30" AND {condition} {CONFIG['order']}'''
        
        queries[name] = {
            'jql': jql,
            'url': f"{CONFIG['server']}/issues/?jql={urllib.parse.quote(jql)}"
        }
    return queries

def connect_jira():
    """Connect to JIRA."""
    try:
        return JIRA(server=CONFIG['server'], basic_auth=CONFIG['auth'])
    except Exception as e:
        print(f"❌ JIRA connection failed: {e}")
        sys.exit(1)

def extract_info(summary):
    """Extract pattern and vehicle from summary - optimized version."""
    # Try PSA pattern first
    if match := re.match(r'^(.*?)\s+PSA(\d+)', summary):
        return match.group(1).strip(), f"PSA{match.group(2)}"
    
    # Try error codes
    if match := re.match(r'^(Err:\d+|[A-Za-z]+:\d+)', summary):
        return match.group(1), "Unknown"
    
    # Fallback
    fallback = re.match(r'^([^,\(]{1,50})', summary)
    return (fallback.group(1).strip() if fallback else summary[:50]), "Unknown"

def process_issues(issues):
    """Process and group issues efficiently."""
    patterns = defaultdict(list)
    vehicle_counts = defaultdict(Counter)
    
    for issue in issues:
        pattern, vehicle = extract_info(issue.fields.summary)
        assignee = getattr(issue.fields.assignee, 'displayName', 'Unassigned')
        
        vehicle_counts[pattern][vehicle] += 1
        patterns[pattern].append({
            'key': issue.key,
            'summary': issue.fields.summary,
            'status': issue.fields.status.name,
            'assignee': assignee,
            'vehicle': vehicle
        })
    
    return {pattern: {
        'issues': issue_list,
        'vehicle_count': dict(vehicle_counts[pattern]),
        'total_count': sum(vehicle_counts[pattern].values())
    } for pattern, issue_list in patterns.items()}

def format_vehicle_stats(vehicle_counts):
    """Format vehicle statistics efficiently."""
    if not vehicle_counts:
        return "0 vehicles"
    
    total = sum(vehicle_counts.values())
    vehicles = [f"{v.replace('PSA', '') if v.startswith('PSA') else v} ({c})" 
                for v, c in sorted(vehicle_counts.items())]
    return f"{total} vehicles: {', '.join(vehicles)}"

def export_all_to_csv(all_results, start_date, end_date):
    """Export all query results to a single CSV file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_range = f"{start_date}_to_{end_date}".replace("-", "")
    filename = f"jira_all_issues_{date_range}_{timestamp}.csv"
    
    fieldnames = ['Query_Type', 'Pattern', 'Vehicle_Stats', 'Issue_Key', 'Vehicle', 'Summary', 'Status', 'Assignee']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames)
        writer.writeheader()
        
        for query_type, data in all_results.items():
            # Section header with query URL
            writer.writerow({
                'Query_Type': f" {query_type.upper()} ISSUES ",
                'Pattern': f"Total: {data['total_count']} issues"
            })
            writer.writerow({
                'Query_Type': 'Query Link:',
                'Pattern': data.get('query_url', '')
            })
            writer.writerow({})
            
            # Write grouped issues
            for pattern, pattern_data in data['grouped_issues'].items():
                issues = pattern_data['issues']
                vehicle_stats = format_vehicle_stats(pattern_data['vehicle_count'])
                
                for i, issue in enumerate(issues):
                    writer.writerow({
                        'Query_Type': query_type if i == 0 else '',
                        'Pattern': pattern if i == 0 else '',
                        'Vehicle_Stats': vehicle_stats if i == 0 else '',
                        'Issue_Key': f"{CONFIG['server']}/browse/{issue['key']}",
                        'Vehicle': issue['vehicle'],
                        'Summary': issue['summary'],
                        'Status': issue['status'],
                        'Assignee': issue['assignee']
                    })
                writer.writerow({})
    
    return filename

def display_results(grouped_issues, query_type=""):
    """Display grouped results to console."""
    if query_type:
        print(f"\n📋 {query_type} Results:")
    
    for pattern, pattern_data in grouped_issues.items():
        issues = pattern_data['issues']
        vehicle_stats = format_vehicle_stats(
            pattern_data['vehicle_count'], 
            pattern_data['total_vehicles']
        )
        
        print(f"\n📊 {pattern} ({len(issues)} issues, {pattern_data['total_vehicles']} vehicles):")
        print(f"   🚗 Vehicle breakdown: {vehicle_stats}")
        
        for issue in issues:
            link = f"https://ventitechnologies.atlassian.net/browse/{issue['key']}"
            print(f"  - {issue['key']} ({issue['vehicle']}): {issue['summary']} "
                  f"(Status: {issue['status']}, Assignee: {issue['assignee']}) - {link}")

def main():
    """Main execution function."""
    print("📅 Enter date range for JIRA query:")
    start_date, end_date = get_date_range()
    
    print(f"✅ Date range: {start_date} to {end_date}")
    print("✅ Connected to JIRA successfully!")
    
    jira_client = connect_jira()
    queries = build_queries(start_date, end_date)
    all_results = {}
    
    # Execute all queries
    for query_name, query_data in queries.items():
        print(f"\n🔍 Executing {query_name} query...")
        print(f"🔗 Query URL: {query_data['url']}")
        try:
            issues = jira_client.search_issues(query_data['jql'], maxResults=False)
            print(f"✅ Found {len(issues)} {query_name.lower()} issues")
            
            if issues:
                grouped_issues = process_issues(issues)
                all_results[query_name] = {
                    'grouped_issues': grouped_issues,
                    'total_count': len(issues),
                    'query_url': query_data['url']
                }
                display_results(grouped_issues, query_name)
            else:
                print(f"No {query_name.lower()} issues found.")
                all_results[query_name] = {
                    'grouped_issues': {}, 
                    'total_count': 0,
                    'query_url': query_data['url']
                }
        
        except Exception as e:
            print(f"❌ {query_name} query failed: {e}")
            all_results[query_name] = {
                'grouped_issues': {}, 
                'total_count': 0,
                'query_url': query_data['url']
            }
    
    # Export and summarize
    if any(result['total_count'] > 0 for result in all_results.values()):
        filename = export_all_to_csv(all_results, start_date, end_date)
        print(f"\n✅ Results exported to: {filename}")
        
        total_issues = sum(result['total_count'] for result in all_results.values())
        print(f"\n📊 Summary:")
        for query_name, result in all_results.items():
            print(f"  {query_name}: {result['total_count']} issues")
        print(f"  Total: {total_issues} issues")
    else:
        print("\n❌ No issues found for any query type.")

if __name__ == "__main__":
    main()