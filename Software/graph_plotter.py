import csv
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone

matplotlib.use('TkAgg')
LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo

def get_datetime_from_text(text):
    # 23/09/2022, 01:07:53
    # https://www.programiz.com/python-programming/datetime/strptime
    text += ' +0800' # Specify timezone
    date_time_obj = datetime.strptime(text, '%d/%m/%Y, %H:%M:%S %z')
    return date_time_obj

def main(filename):
    # Get list of datetime from the CSV file
    print(f"Reading from file: {filename}")
    data = dict()
    with open(filename) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        next(csv_reader, None)  # skip the header
        # Store datetime list for each dict key
        for row in csv_reader:
            date_time_obj = get_datetime_from_text(row[1])
            door = row[2]
            # Create empty list for the first time
            if door not in data:
                data[door] = []
            # Add the datetime into the list
            data[door].append(date_time_obj)

    # Convert to matplotlib date format
    mpl_data = dict()
    for key, value in data.items():
        mpl_data[key] = mdates.date2num(value)

    # Calculate number of bins
    combined_data = sum(data.values(), []) # https://stackoverflow.com/a/716489
    datetime_range = combined_data[-1] - combined_data[0] # Time delta between first and last item
    bins = int(datetime_range.total_seconds() / 60 / 15) # 1 bin every 15 minutes

    # Plot histogram
    # https://stackoverflow.com/questions/29672375/histogram-in-matplotlib-time-on-x-axis
    print(f'Plotting with {bins} bins')
    fig, ax = plt.subplots(1, 1, figsize=(15, 6))
    list_color = ['green', 'blue', 'red', 'yellow']
    list_label = list(mpl_data.keys())
    list_data = mpl_data.values()
    ax.hist(list_data, label=list_label, bins=bins, stacked=True, color=list_color)
    ax.set_xticklabels(ax.get_xticks(minor=True), minor=True)
    ax.xaxis.set_tick_params(rotation=90, which='both')
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1, tz=LOCAL_TIMEZONE))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('(%a) %d %b %H:%M', tz=LOCAL_TIMEZONE))
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[0, 3, 6, 9, 12, 15, 18, 21], tz=LOCAL_TIMEZONE))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H:%M', tz=LOCAL_TIMEZONE))
    ax.grid()
    ax.legend(loc="upper left")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.title(filename)
    plt.savefig('Figure.png')
    plt.show()
    print("Done")

if __name__ == '__main__':
    filename = 'DHCapacityRecords.csv'
    main(filename)