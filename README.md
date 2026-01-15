# Hello Parlant

- <https://www.parlant.io>
- <https://github.com/emcie-co/parlant>

## Quickstart

```bash
.\setup.bat
```

```bash
.\run.bat zhipu
.\run.bat ollama
.\run.bat emcie
```

```bash
http://localhost:8800/
```

### Snapshot

```sh
PS D:\coding\hello-parlant> .\run.bat
...
2025-11-04T06:09:25.368089Z [info     ] [<main>] Try the Sandbox UI at http://localhost:8800
```

## Weather Agent

```bash
.\run_weather.bat
```

```bash
http://localhost:8800/
```

|小天|用户|
|:--|--:|
||北京天气|
|您好，北京今天的天气情况是这样的：||
|今天北京的气温是15°C，天气晴朗，湿度45%。如果您想知道华氏度的话，可以这样换算：°F = °C × 1.8 + 32。||
||天气怎么样|
|根据北京今天的天气情况，可以这样描述：||
|今天北京的天气是多云，温度大约在15°C左右，湿度45%。如果想知道华氏度的话，可以这样转换：°F = °C × 1.8 + 32。||

|小天|用户|
|:--|--:|
||天气怎么样|
|您好，关于今天的天气情况，我可以帮您查询。||
|请问您想查询哪里的天气呢？比如北京、上海或者深圳。||
||深圳|
|已经为您查到了深圳今天的天气：温度18°C，多云，湿度70%。还有其他城市想查询吗？||

[Weather Agent示例，Parlant底层(Journey 和 Guideline)运行机制](weather_agent.md)

## Journey 和 Guideline原理
[Journey 和 Guideline 源代码分析](journey-guideline-analysis/README.md)