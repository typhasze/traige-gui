#!/usr/bin/env python3
"""
JIRA Issues Analyzer - Fetches and groups JIRA issues by pattern with vehicle analysis.
"""

from jira import JIRA
from collections import defaultdict
import re
import csv
from datetime import datetime
import sys
import urllib.parse

# Configuration
JIRA_CONFIG = {
    'server': 'https://ventitechnologies.atlassian.net',
    'email': 'hafiz.kosno@ventitechnologies.com',
    'token': 'ATATT3xFfGF0NH9UwB1voANOi6euu8tpV3zfH-CM9S2wzQjF7LJO0HHG4z1qmaNCUKRz9Vt4DuBROnhp2vgwfux4Fjl9Dj0ADwd6HDxLvZUYS_EB1dtDroUC2zQaWBcVxzOxp8kUlrCvr9iododlYnu999OA8n9OSR6XTLexiC4bkdenRqA2QDc=CFD797F7'
}

QUERY_TYPES = {
    'Non-Operational': '"intervention type[dropdown]" = "Direct Intervention" AND "issue criticality[dropdown]" IN (Critical, "P1 Critical", Non-Critical) AND status NOT IN (Invalid)',
    'Operational': '"intervention type[dropdown]" = "Direct Intervention" AND "issue criticality[dropdown]" IN (Operational) AND status NOT IN (Invalid)',
    'E-Stop': 'summary ~ "e_stop"'
}

def get_date_input(prompt):
    """Get validated date input from user."""
    while True:
        try:
            date_str = input(prompt).strip()
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            print("❌ Invalid format. Use YYYY-MM-DD (e.g., 2025-08-25)")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled.")
            sys.exit(0)

def build_jql_queries(start_date, end_date):
    """Build JQL queries for all issue types."""
    if datetime.strptime(start_date, '%Y-%m-%d') >= datetime.strptime(end_date, '%Y-%m-%d'):
        print("❌ Start date must be before end date.")
        sys.exit(1)
    
    base = f'''project = BUG AND type = Bug AND labels = psa_driverless 
               AND "date and time[time stamp]" >= "{start_date} 07:30" 
               AND "date and time[time stamp]" < "{end_date} 07:30"'''
    
    order = 'ORDER BY cf[10052] ASC, cf[10312] ASC, summary ASC, cf[10084] ASC, created DESC'
    
    queries = {}
    for name, condition in QUERY_TYPES.items():
        jql_query = f"{base} AND {condition} {order}"
        query_url = f"https://ventitechnologies.atlassian.net/issues/?jql={urllib.parse.quote(jql_query)}"
        queries[name] = {
            'jql': jql_query,
            'url': query_url
        }
    
    return queries

def connect_to_jira():
    """Connect to JIRA and return client."""
    print("🔗 Connecting to JIRA...")
    try:
        return JIRA(server=JIRA_CONFIG['server'], 
                   basic_auth=(JIRA_CONFIG['email'], JIRA_CONFIG['token']))
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

def extract_pattern(summary):
    """Extract grouping pattern from issue summary."""
    # First try to match patterns with PSA numbers
    match = re.match(r'^(.*?)\s+PSA\d+', summary)
    if match:
        return match.group(1).strip()
    
    # For other patterns like "Err:510", return the first part before any timestamp or details
    # Match patterns like "Err:510" or other error codes
    error_match = re.match(r'^(Err:\d+|[A-Za-z]+:\d+)', summary)
    if error_match:
        return error_match.group(1)
    
    # Fallback: return first 50 characters or until first comma/parenthesis
    fallback_match = re.match(r'^([^,\(]{1,50})', summary)
    return fallback_match.group(1).strip() if fallback_match else summary[:50]

def extract_vehicle(summary):
    """Extract vehicle ID from summary."""
    match = re.search(r'PSA(\d+)', summary)
    return f"PSA{match.group(1)}" if match else "Unknown"

def process_issues(issues):
    """Process and group issues by pattern with vehicle analysis."""
    grouped = defaultdict(list)
    vehicle_counts = defaultdict(lambda: defaultdict(int))
    
    for issue in issues:
        pattern = extract_pattern(issue.fields.summary)
        vehicle = extract_vehicle(issue.fields.summary)
        assignee = issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'
        
        vehicle_counts[pattern][vehicle] += 1
        grouped[pattern].append({
            'key': issue.key,
            'summary': issue.fields.summary,
            'status': issue.fields.status.name,
            'assignee': assignee,
            'vehicle': vehicle
        })
    
    # Transform to include vehicle statistics
    return {pattern: {
        'issues': issues_list,
        'vehicle_count': dict(vehicle_counts[pattern]),
        'total_vehicles': sum(vehicle_counts[pattern].values()),  # Total number of issues, not unique vehicles
        'total_issues': len(issues_list)
    } for pattern, issues_list in grouped.items()}

def format_vehicle_stats(vehicle_counts, total_vehicles):
    """Format vehicle statistics for display."""
    vehicle_list = []
    for vehicle, count in sorted(vehicle_counts.items()):
        vehicle_id = vehicle.replace("PSA", "") if vehicle.startswith("PSA") else vehicle
        vehicle_list.append(f"{vehicle_id} ({count})")
    return f"{total_vehicles} vehicles: " + ", ".join(vehicle_list)

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
                vehicle_stats = format_vehicle_stats(
                    pattern_data['vehicle_count'], 
                    pattern_data['total_vehicles']
                )
                
                for i, issue in enumerate(issues):
                    writer.writerow({
                        'Query_Type': query_type if i == 0 else '',
                        'Pattern': pattern if i == 0 else '',
                        'Vehicle_Stats': vehicle_stats if i == 0 else '',
                        'Issue_Key': f"https://ventitechnologies.atlassian.net/browse/{issue['key']}",
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
    start_date = get_date_input("Start date (YYYY-MM-DD): ")
    end_date = get_date_input("End date (YYYY-MM-DD): ")
    
    print(f"✅ Date range: {start_date} to {end_date}")
    print("✅ Connected to JIRA successfully!")
    
    jira_client = connect_to_jira()
    queries = build_jql_queries(start_date, end_date)
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