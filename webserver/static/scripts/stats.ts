import Highcharts from "highcharts/highstock";

interface StatsProps {
    stats_url: string;
}

const propsElement = document.getElementById("page-props");
let pageProps: StatsProps | undefined;
if (propsElement?.innerHTML) {
    pageProps = JSON.parse(propsElement!.innerHTML);
}

fetch(pageProps!.stats_url)
    .then((res) => res.json())
    .then((data: any) => {
        // Create the chart
        Highcharts.stockChart("chart", {
            rangeSelector: { selected: 5 },
            series: data,
            yAxis: { min: 0 },
            tooltip: { valueDecimals: 0 },
            credits: { enabled: false },
        });
    });
