# Optional companion JSON file
The optional companion file series\_config\.json can define overrides and multiseries config sections to control conversion behavior.
## Overrides
Use overrides to set or replace OMIDS header values for specific series.
### Syntax
- overrides is an object where keys are series numbers or list expressions.
- Values are objects of header keys and override values. -\ A list expression can be used for series numbers or override values.
- List expression format: [\<start\>:\<step\>:\<end\>] or [\<start\>:\<step\>:n\<count\>] 
  - Integers: [1:2:11] or [1:2:n3]
  - Floats: [0.5:0.5:2.0] or [0.5:0.5:n4]
- When a list is used as an override value and its length matches the series list length, each series receives its corresponding value.

## multiseries config
Use multiseries config to group multiple series into a single concatenated 4D volume.
### Syntax
- The top-level object contains group names and their series lists.
- Each group value is either:
  - A list of series numbers or relative paths, or
  - A list expression.
- Series numbers are compared with DICOM tag 0020,0011.
- Paths are resolved relative to the input folder and compared using absolute paths.

### Notes
- When all series in a group are present, volumes are concatenated and saved as a single file.
- The group name is only used for tracking; output naming follows the converter’s rules.

## Example
```python
{
  "overrides": {
     "3": {
       "Modality": "MR"
     }, 
     "[10:1:12]": {
       "EchoTime": "[10:5:n3]"
     }
  },
  "T1_group": [1,2,3],
  "fMRI_group": "[4:1:8]", 
  "local_paths_group": ["subdir/seriesA", "subdir/seriesB"]
}
```