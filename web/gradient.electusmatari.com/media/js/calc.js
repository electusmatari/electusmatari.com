function humaneint (num) {
    if (num < 0) {
        prefix = "-";
        num *= -1;
    } else {
        prefix = "";
    }
    num = num + "";
    s = "";
    while (num.length > 3) {
        if (s.length > 0) {
            s = "," + s;
        }
        s = num.substr(num.length - 3) + s;
        num = num.substr(0, num.length - 3);
    }
    if (num.length > 0) {
        if (s.length > 0) {
            s = num + "," + s;
        } else {
            s = num;
        }
    }
    return prefix + s;
}

function humane (num) {
    num = num.toFixed(2) + "";
    postcomma = num.substr(-2);
    precomma = num.substr(0, num.length - 3);
    return humaneint(precomma) + "." + postcomma;
}

function calculator (result, search, data, table) {
    quantities = [];
    for (i in table) {
        quantities[i] = 0;
    }
    function write_table () {
        needle = new RegExp(search.val(), "i");
        html = '<table class="data">';
        html += '<thead>'
        html += '<tr><th>Qty</th><th>Typename</th><th>Price</th></tr>';
        html += '</thead>'
        rowi = 1;
        for (row in table) {
            typename = table[row].name;
            group = table[row].type
            if (typename.search(needle) == -1 && group.search(needle) == -1) {
                continue;
            }
            if (rowi % 2) {
                cls = "odd";
            } else {
                cls = "even";
            }
            rowi += 1;
            if (quantities[row]) {
                qty = quantities[row];
            } else {
                qty = "";
            }
            html += ('<tr id="tr' + row + '" class="' + cls + '">' +
                     '<td class="qty">' +
                     '<input type="text" size="7" name="qty' + row + '" ' +
                     'id="dataqty' + row + '" ' +
                     'value="' + qty + '" autocomplete="off" />' +
                     '</td>' +
                     '<td class="name"><label for="dataqty' + row + '">' +
                     table[row].name + "</label></td>" +
                     '<td class="numeric">' + humane(table[row].value) + "</td>" +
                     '</tr>');
        }
        html += '</table>';
        data.html(html);
        data.find("input").blur(write_results_from_data);
        data.find("input").keydown(update_results_from_data);
    }

    function update_table () {
        needle = search.val();
        if (needle.length == 0 || needle.length >= 3) {
            write_table();
        }
    }

    function write_results () {
        total = 0;
        html = '<table class="data">';
        html += '<thead>'
        html += '<tr><th colspan="2">Quantity</th><th>Type</th><th>p.u.</th>';
        html += '<th>Price</th></tr>';
        html += '</thead>'
        clsi = 1;
        for (rowi in table) {
            qty = quantities[rowi];
            if (qty) {
                if (clsi % 2) {
                    cls = "odd";
                } else {
                    cls = "even";
                }
                clsi += 1;
                i = $(this).attr("name").substr(3);
                typename = table[rowi].name;
                price = table[rowi].value;
                html += ('<tr class="' + cls + '">' +
                         '<td>' +
                         '<input type="text" size="7" ' +
                         'name="qty' + rowi + '" ' +
                         'id="resultqty' + rowi + '" ' +
                         'value="' + qty + '" autocomplete="off" />' +
                         '</td>' +
                         '<td class="numeric">' +
                         humaneint(parseInt(qty)) +
                         '</td>' +
                         '<td class="name">' +
                         '<label for="resultqty' + rowi + '">' + typename +
                         '</label></td>' +
                         '<td class="numeric">' + humane(price) +
                         '</td>' +
                         '<td class="numeric">' + humane(qty*price) +
                         '</td>' +
                         '</tr>');
                total += qty*price;
            }
        }
        $(".calcmod").each(function () {
                if ($(this).attr("checked")) {
                    total *= parseFloat($(this).attr("value"));
                }
            });
        html += '<tfoot>';
        html += '<tr class="total"><th colspan="4">Total:</td>';
        html += '<td class="numeric">' + humane(total) + '</td></tr>';
        html += '</tfoot>';
        html += "</table>";
        result.html(html);
        result.find("input").blur(write_results_from_results);
        result.find("input").keydown(update_results_from_results);
    }

    function update_results_from_data (e) {
        if (e.keyCode == 13) {
            write_results_from_data();
            return false;
        }
    }

    function write_results_from_results () {
        result.find("input").each(function () {
                qty = $(this).val();
                rowi = parseInt($(this).attr("name").substr(3));
                data.find("input[name=qty" + rowi + "]").val(qty);
                if (!qty) {
                    qty = 0;
                }
                quantities[rowi] = qty;
            });
        write_results();
    }

    function write_results_from_data () {
        data.find("input").each(function (i) {
                qty = $(this).val();
                if (!qty) {
                    qty = 0;
                }
                rowi = parseInt($(this).attr("name").substr(3));
                quantities[rowi] = qty;
            });
        write_results();
    }

    function update_results_from_results (e) {
        if (e.keyCode == 13) {
            write_results_from_results();
            return false;
        }
    }


    timeout = null;
    function search_changed () {
        if (timeout) {
            clearTimeout(timeout);
        }
        timeout = setTimeout(update_table, 10);
    }

    search.attr("autocomplete", "off");
    search.keydown(search_changed);
    search.focus();
    write_table();
    write_results();
    $(".calcmod").change(write_results);
}
