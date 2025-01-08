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
python coloc_plot.py dataset_A.h.tsv.gz dataset_B.h.tsv.gz 10 45274176 45546119 --x_line 45374176 45446119
```

### Example Output

![image](https://github.com/user-attachments/assets/3c095a72-2c0d-4f0a-8000-3d2de8f05fe6)

Where the top axis corresponds to dataset A (appearing first in the command) and the bottom axis corresponds to dataset B (appearing second in the command). The directions of the triangles (pointing up or down) corresponds to the direction of the beta of the top variants (i.e., pointing up for a positive beta).
