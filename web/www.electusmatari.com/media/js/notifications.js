// Electus Matari notification system
// Operation notifications and Gradient ticket system & shop
// notifications.

var opnotify_delay = 60 * 5 * 1000; // Every 5 minutes

function set_html(elementid, html) {
    $$(elementid).each(function (element) {
        element.update(html);
    });
}

function notifications_init () {
    opnotify_init();
    status_init();
    regular_op_time();
}

//////////////////////////////////////////////////////////////////
// Updating time string

// Requires:
// An element with id opcurrenttime

function get_time_string() {
    var d = new Date();
    var weekday = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getUTCDay()];
    var hour = d.getUTCHours();
    if (hour < 10) {
        hour = '0' + hour;
    }
    var minute = d.getUTCMinutes();
    if (minute < 10) {
        minute = '0' + minute;
    }
    var optext = weekday + ' | ' + hour + ':' + minute + ' | ';

    if (location.search.search("opexpand") == -1) {
        return optext;
    } else {
        var year = d.getUTCFullYear() - 1898;
        var month = d.getUTCMonth() + 1;
        if (month < 10) {
            month = '0' + month;
        }
        var day = d.getUTCDate();
        if (day < 10) {
            day = '0' + day;
        }
        return year + "." + month + "." + day + " " + optext;
    }
}

function regular_op_time() {
    set_html("#opcurrenttime", get_time_string());
    setTimeout(regular_op_time, 5000);
}

//////////////////////////////////////////////////////////////////
// Operation Notifications

// Requires:
// An element with id #opnotifications

function opnotify_init () {
    opnotify_set_html();
    opnotify_schedule();
}

function opnotify_set_html () {
    if (window.webkitNotifications == undefined) {
        set_html("#opnotifications",
                 '<a class="opnotifylink" href="/notify/notsupported/">' +
                 'Notifications not supported</a>'
                );
    } else if (window.webkitNotifications.checkPermission() != 0) {
        set_html("#opnotifications",
                 '<a class="opnotifylink" onClick="opnotify_request(); ' +
                 'return false;">' +
                 'Notifications disabled</a>'
                );
    } else {
        set_html("#opnotifications",
                 '<a class="opnotifylink" onClick="opnotify_request(); ' +
                 'return false;">' +
                 'Notifications enabled</a>'
                );
    }
}

function opnotify_schedule () {
    opnotify_check();
    setTimeout(opnotify_schedule, opnotify_delay);
}

function opnotify_request () {
    window.webkitNotifications.requestPermission(function () {
        if (window.webkitNotifications.checkPermission() == 0) {
            opnotify_set_html();
        }
    });
}

function opnotify_check () {
    new Ajax.Request('/notify/json/opnotify/', {
        method: 'get',
        onSuccess: function (transport) {
            var data = JSON.parse(transport.responseText);
            var now = new Date().getTime() / 1000;
            var in15m = now + 15 * 60;
            var in1h = now + 60 * 60;
            var tooold = now - 60 * 60;
            var cookie = Cookie.get('opnotify_announced');
            if (cookie) {
                var announced = JSON.parse(cookie);
            } else {
                var announced = {'now': {}, 'in15m': {}, 'in1h': {}};
            }
            var inthis = {};
            var n = 1;

            for (var i = 0; i < data.length; i++) {
                obj = data[i];
                inthis[obj.tid] = true;
                if (obj.time < tooold) {
                    continue;
                } else if (obj.time < now) {
                    if (obj.time != announced.now[obj.tid]) {
                        opnotify_notify(obj);
                        announced.now[obj.tid] = obj.time;
                    }
                } else if (obj.time < in15m) {
                    if (obj.time != announced.in15m[obj.tid]) {
                        opnotify_notify(obj);
                        announced.in15m[obj.tid] = obj.time;
                    }
                } else if (obj.time < in1h) {
                    if (obj.time != announced.in1h[obj.tid]) {
                        opnotify_notify(obj);
                        announced.in1h[obj.tid] = obj.time;
                    }
                }
            }
            for (timestr in announced) {
                for (tid in announced[timestr]) {
                    if (!(tid in inthis)) {
                        delete announced[timestr][tid];
                    }
                }
            }
            Cookie.set('opnotify_announced', JSON.stringify(announced));
        }
    });
}

function opnotify_notify (obj) {
    var now = new Date().getTime() / 1000;
    var minutes = Math.round((obj.time - now) / 60);
    if (minutes < 0) {
        var title = "Operation started " + -minutes + " minute" +
            (minutes != 1 ? "s" : "") + " ago";
    } else {
        var title = "Operation starts in " + minutes + " minute" +
            (minutes != 1 ? "s" : "");
    }
    window.webkitNotifications.createNotification(
        "http://www.electusmatari.com/media/img/emlogo.png",
        title,
        obj.text + ' by: ' + obj.username
    ).show();
}

//////////////////////////////////////////////////////////////////
// Status updates

// Requires:
// An element with id #emstatus

function status_update (status_list) {
    if (status_list.length == 0) {
        return;
    }
    var links = [];
    for (var i = 0; i < status_list.length; i++) {
        message = status_list[i];
        links.push('<a href="' + message.url + '">' + message.text + '</a>');
    }
    set_html("#emstatus", "(" + links.join(", ") + ")");
}

function status_init (){
    new Ajax.Request('/notify/json/status/', {
        method: 'get',
        onSuccess: function(transport) {
            var data = JSON.parse(transport.responseText);
            status_update(data);
        }
    });
}

//////////////////////////////////////////////////////////////////

Event.observe(document, "dom:loaded", notifications_init);
