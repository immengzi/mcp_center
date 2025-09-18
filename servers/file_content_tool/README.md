# 文件内容控制工具MCP（管理控制程序）规范文档

## 一、服务介绍
本服务是一款基于Linux核心文本处理命令（`grep`/`sed`/`awk`/`sort`/`unique`/`echo`）实现的文件内容控制MCP（管理控制程序），核心功能为对本地或远程服务器的文本文件进行**搜索、替换、处理、排序、去重、内容写入**等精细化操作，为日志分析、配置文件修改、数据清洗等场景提供灵活、高效的自动化工具集。


## 二、核心工具信息

| 工具名称 | 工具功能 | 核心输入参数 | 关键返回内容 |
| ---- | ---- | ---- | ---- |
| `file_grep_tool` | 通过`grep`命令搜索文件中匹配指定模式的内容（支持正则、大小写忽略等） | - `file_path`：目标文件路径（绝对路径，必填）<br>- `pattern`：搜索模式（支持正则，如"error"，必填）<br>- `options`：`grep`可选参数（如"-n"显示行号、"-i"忽略大小写，可选）<br>- `host`：远程主机名/IP（默认`localhost`，本地操作可不填）<br>- `port`：SSH端口（默认22，远程操作时使用）<br>- `username`：SSH用户名（默认`root`，远程操作时需指定）<br>- `password`：SSH密码（远程操作时必填） | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"本地文件搜索完成"）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `file_path`：目标文件路径<br>&nbsp;&nbsp;- `result`：匹配结果列表（每行一个匹配项） |
| `file_sed_tool` | 通过`sed`命令替换文件中匹配的内容（支持全局替换、原文件修改） | - `file_path`：目标文件路径（绝对路径，必填）<br>- `pattern`：替换模式（如"s/old/new/g"，`g`表示全局替换，必填）<br>- `in_place`：是否直接修改原文件（布尔值，默认`False`，仅输出结果）<br>- `options`：`sed`可选参数（如"-i.bak"备份原文件，可选）<br>- `host`/`port`/`username`/`password`：同`file_grep_tool` | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"远程sed执行成功"）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `file_path`：目标文件路径<br>&nbsp;&nbsp;- `result`：替换后内容（`in_place=False`时返回） |
| `file_awk_tool` | 通过`awk`命令对文本文件进行高级处理（支持列提取、条件过滤） | - `file_path`：目标文件路径（绝对路径，必填）<br>- `script`：`awk`处理脚本（如"'{print $1,$3}'"提取1、3列，必填）<br>- `options`：`awk`可选参数（如"-F:"指定分隔符为冒号，可选）<br>- `host`/`port`/`username`/`password`：同`file_grep_tool` | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"本地awk处理成功"）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `file_path`：目标文件路径<br>&nbsp;&nbsp;- `result`：处理结果列表（每行一个结果项） |
| `file_sort_tool` | 通过`sort`命令对文本文件进行排序（支持按列、升序/降序） | - `file_path`：目标文件路径（绝对路径，必填）<br>- `options`：`sort`可选参数（如"-n"按数字排序、"-k2"按第2列排序、"-r"降序，可选）<br>- `output_file`：排序结果输出路径（可选，默认不保存到文件）<br>- `host`/`port`/`username`/`password`：同`file_grep_tool` | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"远程排序完成"）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `file_path`/`output_file`：目标文件/输出文件路径<br>&nbsp;&nbsp;- `result`：排序结果列表（`output_file`为空时返回） |
| `file_unique_tool` | 通过`unique`命令对文本文件进行去重（支持统计重复次数） | - `file_path`：目标文件路径（绝对路径，必填）<br>- `options`：`unique`可选参数（如"-u"仅显示唯一行、"-c"统计重复次数，可选）<br>- `output_file`：去重结果输出路径（可选，默认不保存到文件）<br>- `host`/`port`/`username`/`password`：同`file_grep_tool` | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"本地去重完成"）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `file_path`/`output_file`：目标文件/输出文件路径<br>&nbsp;&nbsp;- `result`：去重结果列表（`output_file`为空时返回） |
| `file_echo_tool` | 通过`echo`命令向文件写入内容（支持覆盖/追加模式） | - `content`：要写入的内容（如"Hello World"，必填）<br>- `file_path`：目标文件路径（绝对路径，必填）<br>- `append`：是否追加内容（布尔值，默认`False`，覆盖原文件）<br>- `host`/`port`/`username`/`password`：同`file_grep_tool` | - `success`：操作是否成功（布尔值）<br>- `message`：操作结果描述（如"本地写入成功"）<br>- `data`：包含操作详情的字典<br>&nbsp;&nbsp;- `host`：操作的主机名/IP<br>&nbsp;&nbsp;- `file_path`：目标文件路径<br>&nbsp;&nbsp;- `action`：操作类型（"overwrite"覆盖/"append"追加） |


## 三、工具使用说明
1. **本地操作规则**：  
   不填写`host`、`username`、`password`参数，默认对本机（`localhost`）文件进行操作，仅需提供`file_path`、`pattern`（或`script`/`content`）等核心业务参数。
   
2. **远程操作规则**：  
   必须提供`host`（远程主机IP/hostname）、`username`（SSH用户名）、`password`（SSH密码），`port`可选（默认22）；远程文件路径需使用**绝对路径**（如`/var/log/syslog`），避免相对路径导致的文件找不到问题。

3. **命令参数说明**：  
   - 所有工具的`options`参数需遵循Linux原生命令语法（如`grep`的"-i"、`sed`的"-i.bak"），不支持自定义参数；  
   - `file_sed_tool`的`pattern`需包含`s/`（替换标识），如"s/old_value/new_value/g"表示全局替换"old_value"为"new_value"；  
   - `file_awk_tool`的`script`需用单引号包裹（如"'{print $1}'"），确保列提取、条件判断等逻辑生效。


## 四、注意事项
- **权限控制**：操作文件需具备对应权限（本地操作可能需要`sudo`，远程操作需SSH用户对目标文件有`r`（读）/`w`（写）权限，可通过`chmod`命令调整）。
- **大文件处理**：处理GB级大文件时，建议通过`output_file`参数将结果保存到文件，避免内存溢出（直接返回结果列表可能占用大量内存）。
- **特殊字符处理**：`content`（`file_echo_tool`）、`pattern`（`file_grep_tool`）中的单引号需提前转义（工具已内置单引号转义逻辑，无需手动处理），避免命令语法错误。
- **系统兼容性**：`awk`/`sed`等命令的部分参数可能因操作系统版本存在差异（如CentOS与Ubuntu的`sed`备份参数格式一致，但部分扩展功能不同），建议通过`get_kill_signals`（进程控制工具）或`man`命令确认目标系统支持的参数。