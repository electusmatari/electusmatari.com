var agenda = [];
var running = false;

function Feed (options) {
    var feed = this;
    this.name = options.name;
    this.buttonelt = "#" + options.id + "b";
    this.infoelt = "#" + options.id + "i";
    this.url = options.url;
    this.proc = options.proc;
    this.click = function () {
        $(this.infoelt).html('<img src="/media/img/icons/loading.gif" />');
        $("#startstopi").html('<img src="/media/img/icons/loading.gif" />');
        $.ajax({
            url: feed.url,
            error: function () {
                $(feed.infoelt).html("Failed to load data.");
                agenda = [];
                feed.agenda_changed();
            },
            success: function (data) {
                $(feed.infoelt).html('');
                agenda = [];
                for (i in data) {
                    agenda.push({feed: feed,
                                 arg: data[i]});
                }
                feed.agenda_changed();
                if (agenda.length > 0) {
                    start();
                }
            }
        });
    };
    this.initialize = function () {
        $(this.buttonelt).click(this.click);
        $(this.infoelt).html('<img src="/media/img/icons/loading.gif" />');
        $.ajax({
            url: feed.url,
            error: function () {
                $(feed.infoelt).html("Failed to load data.");
            },
            success: function (data) {
                update_info(feed.infoelt, data.length);
            }
        });
    };
    this.agenda_changed = function () {
        update_info(this.infoelt, agenda.length);
        update_info("#startstopi", agenda.length);
        if (agenda.length > 0) {
            $("#startstopb").removeAttr("disabled");
        } else {
            $("#startstopb").attr("disabled", "disabled");
        }
    };
}

var feed_list = [
    new Feed({name: "Price History",
              id: "history",
              url: "/uploader/json/suggest/markethistory/",
              proc: function (typeid) {
                  CCPEVE.showMarketDetails(typeid);
              }}),
    new Feed({name: "Market Data",
              id: "orders",
              url: "/uploader/json/suggest/marketorders/",
              proc: function (typeid) {
                  CCPEVE.showMarketDetails(typeid);
              }}),
    new Feed({name: "Amarr Militia Corps",
              id: "corps",
              url: "/uploader/json/suggest/corporations/",
              proc: function (corpid) {
                  CCPEVE.showInfo(2, corpid);
              }}),
];

function schedule () {
    if (running && agenda.length > 0) {
        var elt = agenda.shift();
        elt.feed.proc(elt.arg);
        elt.feed.agenda_changed();
    }
    setTimeout(schedule, 3000);
}

function update_info (infoelt, length) {
    if (length == 0) {
        $(infoelt).html("No items left.");
    } else {
        $(infoelt).html(length + " item" + (length==1?"":"s") + " left, " +
                        "estimated " + Math.round(length*3*10/60.0)/10.0 +
                        " minutes.");
    }
}

function start () {
    $('#startstopb').html("Pause");
    $('#startstopb').click(stop);
    $("#startstopb").removeAttr("disabled");
    update_info("#startstopi", agenda.length);
    running = true;
}

function stop () {
    $('#startstopb').html("Resume");
    $('#startstopb').click(start);
    $("#startstopb").removeAttr("disabled");
    update_info("#startstopi", agenda.length);
    running = false;
}

$(function () {
    for (i in feed_list) {
        feed_list[i].initialize();
    }
    schedule();
});
