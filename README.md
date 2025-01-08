# pgx-ml-t-tools
Repository to share tools made for pharmacogenomics lab that may be helpful for future learners and projects



## coloc_plot.py

This tool will generate a colocalization plot; a type of plot that displays the associations of local variants to two different outcomes.

### Arguments

#### Positional Arguments

These arguments are required to run the script.

- `df_A` (str):  
  Path to the first dataset.

- `df_B` (str):  
  Path to the second dataset.

- `chromosome` (str):  
  The chromosome to filter the data by (e.g., 1, 2, X).

- `lower` (int):  
  The lower bound of the base pair location. This value defines the start of the region of interest in the genome.

- `upper` (int):  
  The upper bound of the base pair location. This value defines the end of the region of interest in the genome.

#### Optional Arguments

These arguments are optional and can be included for additional customization.

- `--x_line` (list of int):  
  Optional list of dashed vertical lines to draw on the plot. This is useful for marking gene boundaries or other significant positions along the gene region. Enter the base pair values separated by spaces.  
  Example: `--x_line 100000 200000 300000`

- `--y_line` (list of int):  
  Optional list of dashed horizontal lines to draw on the plot. This is useful for marking significance levels. Enter the -log10(p-value) values separated by spaces.  
  Example: `--y_line 1 2 3`

- `--symmetric` (store_true):  
  If set, the y-axes for both datasets (`df_A` and `df_B`) will be identical (i.e., centers y=0). No value is required for this argument, as it is a flag.  
  Example: `--symmetric`

### Example Usage

```bash
python coloc_plot.py dataset_A.csv dataset_B.csv 1 100000 200000 --x_line 100000 150000 --y_line 1 2 --symmetric
```

### Example Output

![image](https://github.com/user-attachments/assets/478d0b58-dd31-4f6b-a27e-099968f1f26c)
