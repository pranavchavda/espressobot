import json
import subprocess
import datetime
from pytz import timezone
import argparse

def run_graphql(variables, graphql_file, graphql_tool):
    cmd = ['python3', graphql_tool, '--file', graphql_file, '--variables', json.dumps(variables), '--output', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running GraphQL query.\nStderr: {result.stderr}\nStdout: {result.stdout}")
        raise Exception(f"GraphQL query failed: {result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from stdout.\nStdout: {result.stdout}")
        raise

def main():
    parser = argparse.ArgumentParser(
        description="Calculates the total revenue for Shopify orders created since midnight on a given date.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate revenue for today in Toronto time
  python sum_orders_named_fixed.py

  # Calculate revenue for a specific date
  python sum_orders_named_fixed.py --date 2023-10-26
"""
    )
    parser.add_argument('--date', help="Date to calculate revenue for (YYYY-MM-DD). Defaults to today.")
    parser.add_argument('--timezone', default='America/Toronto', help="Timezone for calculation. (default: America/Toronto)")
    parser.add_argument('--limit', type=int, default=1000, help="Maximum number of orders to check. (default: 1000)")
    parser.add_argument('--graphql-file', default='/home/pranav/espressobot/frontend/python-tools/order_final_named_fixed.graphql', help="Path to the GraphQL query file.")
    parser.add_argument('--graphql-tool', default='/home/pranav/espressobot/frontend/python-tools/graphql_query.py', help="Path to the graphql_query.py script.")

    args = parser.parse_args()

    tz = timezone(args.timezone)

    if args.date:
        try:
            target_date = datetime.datetime.strptime(args.date, '%Y-%m-%d').date()
            start_of_day = tz.localize(datetime.datetime.combine(target_date, datetime.time.min))
        except ValueError:
            print("Error: --date must be in YYYY-MM-DD format.")
            return
    else:
        now = datetime.datetime.now(tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_revenue = 0.0
    cursor = None
    fetched_orders = 0
    stop_fetching = False

    print(f"Calculating total revenue for orders on or after {start_of_day.strftime('%Y-%m-%d %H:%M:%S %Z')}...")

    while not stop_fetching:
        variables = {"cursor": cursor}
        try:
            result = run_graphql(variables, args.graphql_file, args.graphql_tool)
        except Exception as e:
            print(e)
            break

        orders = result.get("data", {}).get("orders", {}).get("edges", [])
        if not orders:
            print("No more orders found.")
            break

        for edge in orders:
            node = edge["node"]
            created_at_utc = datetime.datetime.fromisoformat(node["createdAt"].replace('Z', '+00:00'))
            created_at_local = created_at_utc.astimezone(tz)

            if created_at_local < start_of_day:
                stop_fetching = True
                break

            if node.get("cancelledAt") is not None or node.get("test"):
                continue

            amount = float(node["totalPriceSet"]["shopMoney"]["amount"])
            total_revenue += amount

        fetched_orders += len(orders)
        if fetched_orders >= args.limit:
            print(f"Reached fetch limit of {args.limit} orders.")
            break

        page_info = result.get("data", {}).get("orders", {}).get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        
        cursor = orders[-1]["cursor"]

    print(f"\nTotal revenue for {start_of_day.date()}: CAD {total_revenue:.2f}")
    print(f"(Based on checking {fetched_orders} most recent orders)")

if __name__ == '__main__':
    main()
