import re
import sys
import os
import matplotlib.pyplot as plt

# ==========================================
# Style Configuration
# ==========================================
plt.rcParams.update({
    "text.usetex": False,                 
    "font.family": "serif",               
    "mathtext.fontset": "cm",             
    "axes.titlesize": 20,                 # Tăng cỡ chữ tiêu đề
    "axes.labelsize": 16,                 # Tăng cỡ chữ nhãn trục (chữ "Time Slot")
    "xtick.labelsize": 10,                # GIỮ NGUYÊN cỡ chữ số trên trục X (10)
    "ytick.labelsize": 14,                # Tăng cỡ chữ tên CPU trục Y
    "legend.fontsize": 14,                
})

def parse_input(input_filename):
    """
    Parse input file to get system configuration.
    """
    num_cpus = 1
    try:
        with open(input_filename, 'r') as f:
            first_line = f.readline().strip()
            if first_line:
                parts = first_line.split()
                if len(parts) >= 2:
                    num_cpus = int(parts[1])
    except Exception as e:
        print(f"Error reading input file: {e}")
    return num_cpus

def parse_log(filename, num_cpus):
    """
    Parse log file and build intervals for each CPU.
    """
    cpu_state: dict[int, int | None] = {i: None for i in range(num_cpus)}
    cpu_start: dict[int, int] = {i: 0 for i in range(num_cpus)}
    cpu_intervals: dict[int, list[tuple[int, int, int | None]]] = {i: [] for i in range(num_cpus)}
    current_time = None

    time_slot_pattern = re.compile(r"Time slot\s+(\d+)")
    put_pattern = re.compile(r"CPU\s+(\d+):\s+Put process\s+(\d+)\s+to run queue")
    dispatched_pattern = re.compile(r"CPU\s+(\d+):\s+Dispatched process\s+(\d+)")
    processed_pattern = re.compile(r"CPU\s+(\d+):\s+Processed\s+(\d+)\s+has finished")
    stopped_pattern = re.compile(r"CPU\s+(\d+)\s+stopped")

    def close_interval(cpu, end_time):
        duration = end_time - cpu_start[cpu]
        if duration > 0:
            cpu_intervals[cpu].append((cpu_start[cpu], duration, cpu_state[cpu]))
        cpu_start[cpu] = end_time

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            ts_match = time_slot_pattern.search(line)
            if ts_match:
                current_time = int(ts_match.group(1))
                continue

            put_match = put_pattern.search(line)
            if put_match:
                cpu = int(put_match.group(1))
                if cpu in cpu_state and current_time is not None:
                    close_interval(cpu, current_time)
                    cpu_state[cpu] = None
                continue
            
            d_match = dispatched_pattern.search(line)
            if d_match:
                cpu = int(d_match.group(1))
                proc = int(d_match.group(2))
                if cpu in cpu_state:
                    if current_time is not None:
                        close_interval(cpu, current_time)
                    cpu_state[cpu] = proc
                    if current_time is not None:
                        cpu_start[cpu] = current_time
                continue
            
            p_match = processed_pattern.search(line)
            if p_match:
                cpu = int(p_match.group(1))
                if cpu in cpu_state:
                    if current_time is not None:
                        close_interval(cpu, current_time)
                    cpu_state[cpu] = None
                    if current_time is not None:
                        cpu_start[cpu] = current_time
                continue
            
            s_match = stopped_pattern.search(line)
            if s_match:
                cpu = int(s_match.group(1))
                if cpu in cpu_state:
                    if current_time is not None:
                        close_interval(cpu, current_time)
                    cpu_state[cpu] = None
                    if current_time is not None:
                        cpu_start[cpu] = current_time
                continue

    if current_time is not None:
        for cpu in cpu_state:
            close_interval(cpu, current_time + 1)

    return cpu_intervals

def generate_gantt_chart(input_file, log_file, out_img):
    """
    Generate a single Gantt chart.
    """
    num_cpus = parse_input(input_file)
    
    cpu_intervals = parse_log(log_file, num_cpus)
    
    max_time = 0
    for intervals in cpu_intervals.values():
        for start, duration, _ in intervals:
            max_time = max(max_time, start + duration)
    max_time = max(max_time, 1)
    
    process_colors = {
        1: '#fbb4ae', # Pink
        10: '#FFB7B2', # Light Pink/Peach
        3: '#FFDAC1', # Peach
        9: '#E2F0CB', # Light Green
        5: '#B5EAD7', # Mint Green
        6: '#C7CEEA', # Periwinkle/Blue
        7: '#e5d8bd', # Lặp lại từ đầu
        8: '#b3cde3', 
        2: '#ffffcc', 
        4: '#ccebc5',
        None: '#E5E4E2' # Light Gray cho CPU trống
    }
    # -----------------------------------------------
    
    width = max(12, max_time * 0.3)
    fig, ax = plt.subplots(figsize=(width, max(4, num_cpus * 2)))   
    row_height = 4
    row_gap = 6
    yticks = []
    y_labels = []
    
    for cpu, intervals in cpu_intervals.items():
        y = cpu * row_gap
        yticks.append(y + row_height / 2)
        y_labels.append(f"CPU {cpu}") 
        
        for (start, duration, proc) in intervals:
            color = process_colors.get(proc, '#E5E4E2') if proc is not None else '#E5E4E2'
            ax.broken_barh([(start, duration)], (y, row_height),
                           facecolors=color, edgecolor='black', linewidth=0.8)
            
            if proc is not None:
                # Display process label
                ax.text(start + duration/2, y + row_height/2, f"P{proc}",
                        ha='center', va='center', color='black', fontsize=15)
                
    # Set ticks aligned with time slot boundaries
    ax.set_xticks(range(max_time + 1))
    ax.set_xticklabels([str(x) for x in range(max_time + 1)])
    
    # Hide tick marks on X axis
    ax.tick_params(axis='x', which='both', length=0)
    
    # Enable grid at tick boundaries
    ax.grid(axis='x', linestyle='--', color='gray', alpha=0.5)
    
    ax.set_xlabel("Time Slot")
    ax.set_yticks(yticks)
    ax.set_yticklabels(y_labels)
    ax.set_xlim(0, max_time)
    
    os.makedirs(os.path.dirname(out_img) if os.path.dirname(out_img) else '.', exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_img, dpi=300)
    plt.close()
    print(f"Gantt chart saved to: {out_img}")

def main():
    if len(sys.argv) == 4:
        # Single chart mode
        input_file = sys.argv[1]
        log_file = sys.argv[2]
        out_img = sys.argv[3]
        generate_gantt_chart(input_file, log_file, out_img)
    elif len(sys.argv) == 1:
        # Batch mode: generate for all outputs
        input_dir = "input"
        output_dir = "run_outputs"
        charts_dir = "gantt_charts"
        
        os.makedirs(charts_dir, exist_ok=True)
        
        # Get all config files from input directory
        config_files = []
        for f in os.listdir(input_dir):
            input_path = os.path.join(input_dir, f)
            if os.path.isfile(input_path):
                config_files.append(f)
        
        config_files.sort()
        
        
        for config_name in config_files:
            input_path = os.path.join(input_dir, config_name)
            output_path = os.path.join(output_dir, f"{config_name}.txt")
            
            if os.path.exists(output_path):
                chart_name = config_name
                output_chart = os.path.join(charts_dir, f"{chart_name}.png")
                try:
                    generate_gantt_chart(input_path, output_path, output_chart)
                except Exception as e:
                    print(f"[ERROR] Failed to generate chart for {config_name}: {e}")
            else:
                print(f"[SKIP] Output file not found: {output_path}")
        
        print(f"All charts saved to: {charts_dir}/")
    else:
        print("Usage:")
        print("  Single chart:  python gantt.py <input_file> <log_file> <output_image>")
        print("  Batch mode:    python gantt.py")
        sys.exit(1)

if __name__ == '__main__':
    main()
