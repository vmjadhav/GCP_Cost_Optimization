import json

def calculate_bigquery_cost(
    region,
    bytes_processed_tb,
    slots_reserved,
    hours_used=24 * 30
):
    """
    Calculate BigQuery costs for on-demand and flat-rate pricing.

    Args:
        region (str): Region code, e.g., 'us', 'eu'.
        bytes_processed_tb (float): Total TB of data processed by queries (on-demand usage).
        slots_reserved (int): Number of slots reserved (flat-rate).
        hours_used (int): Number of hours slots are used (default is 24*30 = monthly).

    Returns:
        dict: Cost breakdown and total cost in USD.
    """

    # Cost per TB of data processed using on-demand pricing per region (approximate; varies slightly)
    # As of 2024, typical on-demand cost is $5 or $6.25 per TB depending on region and data type
    on_demand_cost_per_tb_by_region = {
        'us': 6.25,   # US region on-demand cost per TB
        'eu': 7.00,   # Example EU region cost, may vary
        # Add more regions and costs if needed
    }

    # Cost per slot-hour for flat-rate pricing
    # This is approximate; flat-rate slots cost around $40 per slot per month; 
    # Monthly cost per slot ~ $40 so hourly ~$0.055 (40 / (24*30))
    # We use hourly slot cost to multiply by hours of usage
    flat_rate_slot_hourly_cost = 0.055  # USD per slot-hour approx

    # Get on-demand cost per TB for the requested region, default to US if unknown
    on_demand_cost_per_tb = on_demand_cost_per_tb_by_region.get(region.lower(), 6.25)

    # Calculate costs
    on_demand_cost = bytes_processed_tb * on_demand_cost_per_tb
    flat_rate_cost = slots_reserved * flat_rate_slot_hourly_cost * hours_used

    total_cost = on_demand_cost + flat_rate_cost

    result =  {
        'region': region,
        'on_demand_tb_processed': bytes_processed_tb,
        'on_demand_cost_per_tb': on_demand_cost_per_tb,
        'on_demand_cost': round(float(on_demand_cost), 2),
        'slots_reserved': slots_reserved.solution_value(),
        'flat_rate_slot_hourly_cost': flat_rate_slot_hourly_cost,
        'hours_used': hours_used,
        'flat_rate_cost': flat_rate_cost.solution_value(),
        'total_cost': round(float(total_cost.solution_value()), 2)
    }
    
    print('#### Bigquery Cost Result :: ', json.dumps(result, indent=4))
    print('------------------------------------------------------------- ')
    return result


"""
# Example usage
if __name__ == "__main__":
    region = 'us'                  # The region your BigQuery datasets reside in
    tb_processed = 500             # Total TB processed in on-demand pricing
    reserved_slots = 100           # Number of flat-rate slots reserved
    hours_per_month = 24 * 30      # Assuming reserved slots are used all month

    cost_details = calculate_bigquery_cost(region, tb_processed, reserved_slots, hours_per_month)

    print(f"BigQuery Cost Details for region '{cost_details['region']}':")
    print(f"On-Demand Usage: {cost_details['on_demand_tb_processed']} TB")
    print(f"On-Demand Cost per TB: ${cost_details['on_demand_cost_per_tb']:.2f}")
    print(f"Total On-Demand Cost: ${cost_details['on_demand_cost']:.2f}")
    print(f"Reserved Slots: {cost_details['slots_reserved']}")
    print(f"Flat-Rate Slot Hourly Cost: ${cost_details['flat_rate_slot_hourly_cost']:.3f}")
    print(f"Hours Used: {cost_details['hours_used']}")
    print(f"Total Flat-Rate Cost: ${cost_details['flat_rate_cost']:.2f}")
    print(f"Grand Total Cost: ${cost_details['total_cost']:.2f}")
"""