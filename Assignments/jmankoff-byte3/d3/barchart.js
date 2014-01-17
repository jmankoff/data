//Width and height
var margin = {top: 20, right: 20, bottom: 30, left: 40},
    w = 960 - margin.left - margin.right,
    h = 500 - margin.top - margin.bottom;


var parseDate = d3.time.format("%Y-%m").parse,
    formatYear = d3.format("02d"),
    formatDate = function(d) { return "Q" + ((d.getMonth() / 3 | 0) + 1) + formatYear(d.getFullYear() % 100); };


var y0 = d3.scale.ordinal().rangeRoundBands([height, 0], .2);

var y1 = d3.scale.linear();

var x = d3.scale.ordinal().rangeRoundBands([0, width], .1, 0);

var xAxis = d3.svg.axis().scale(x)
    .orient("bottom")
    .tickFormat(formatDate);

var nest = d3.nest().key(function(d) { return d.group; });

var drawgraph = function(data) {
    //Original data
    var dataset = [
	[
	    { x: 0, y: 5 },
	    { x: 1, y: 4 },
	    { x: 2, y: 2 },
	    { x: 3, y: 7 },
	    { x: 4, y: 23 }
	],
	[
	    { x: 0, y: 10 },
	    { x: 1, y: 12 },
	    { x: 2, y: 19 },
	    { x: 3, y: 23 },
	    { x: 4, y: 17 }
	],
	[
	    { x: 0, y: 22 },
	    { x: 1, y: 28 },
	    { x: 2, y: 32 },
	    { x: 3, y: 35 },
	    { x: 4, y: 43 }
	]
    ];

    var stack = d3.layout.stack()
	.values(function(d) { return d.values; })
	.x(function(d) { return d.date; })
	.y(function(d) { return d.value; })
	.out(function(d, y0) { d.valueOffset = y0; });

    var color = d3.scale.category10();


    //Create SVG element
    var svg = d3.select("body").append("svg")
	.attr("width", w + margin.left + margin.right)
	.attr("height", h + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    
    // Add a group for each row of data
    var groups = svg.selectAll("g")
	.data(dataset)
	.enter()
	.append("g")
	.style("fill", function(d, i) {
	    return colors(i);
	});
    
    //Create bars
    var rects = groups.selectAll("rect")
	.data(function(d) {return d; })
	.enter()
	.append("rect")
	.on("mouseover", function(d) {
	    //Get this bar's x/y values, then augment for the tooltip
	    var xPosition = parseFloat(d3.select(this).attr("x")) + xScale.rangeBand() / 2;
	    var yPosition = parseFloat(d3.select(this).attr("y")) + 14;
	    
	    d3.select("#tooltip")
		.style("left", xPosition + "px")
		.style("top", yPosition + "px")
		.select("#value")
		.text(d);
	    
	    //Show the tooltip
	    d3.select("#tooltip").classed("hidden", false);
	    
	})
	.on("mouseout", function() {
	    //Remove the tooltip
	    d3.select("#tooltip").classed("hidden", true);
	})
	.attr("x", function(d, i) {
	    return xScale(i);
	})
	.attr("y", function(d) {
	    return h - yScale(d.y0);
	})
	.attr("x", function(d, i) {
	    return xScale(i);
	})
	.attr("y", function(d) {
	    return yScale(d.y0);
	})
	.attr("height", function(d) {
	    return yScale(d.y);
	})
	.attr("width", xScale.rangeBand());
};




