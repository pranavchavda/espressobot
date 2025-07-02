import json
import subprocess
import datetime
from pytz import timezone

def run_graphql(variables):
    cmd = ['python3', '/home/pranav/espressobot/frontend/python-tools/graphql_query.py', '--file', '/home/pranav/espressobot/frontend/python-tools/order_final_named_fixed.graphql', '--variables', json.dumps(variables), '--output', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("GraphQL stdout:", result.stdout)
    print("GraphQL stderr:", result.stderr)
    if result.returncode != 0:
        raise Exception(f"GraphQL query failed: {result.stderr}")
    print("GraphQL stdout:", result.stdout)
    print("GraphQL stderr:", result.stderr)
    return json.loads(result.stdout)

def main():
    et_tz = timezone('America/Toronto')
    now = datetime.datetime.now(et_tz)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_revenue = 0.0
    cursor = None
    fetched_orders = 0

    while True:
        variables = {"cursor": cursor}
        result = run_graphql(variables)
        orders = result["data"]["orders"]["edges"]
        for edge in orders:
            node = edge["node"]

            created_dt = datetime.datetime.fromisoformat(node["createdAt"].replace('Z', '+00:00')).astimezone(et_tz)
            if created_dt < midnight:
                continue

            if node["cancelledAt"] is not None or node["test"]:
                continue

            amount = float(node["totalPriceSet"]["shopMoney"]["amount"])
            total_revenue += amount

            fetched_orders += 1
            if fetched_orders >= 1000:
                print(f"Total revenue since midnight (Toronto time): CAD {total_revenue:.2f}")
                return

        page_info = result["data"]["orders"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = orders[-1]["cursor"]

    print(f"Total revenue since midnight (Toronto time): CAD {total_revenue:.2f}")

if __name__ == '__main__':
    main()
