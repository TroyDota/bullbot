if (!String.prototype.format) {
    String.prototype.format = function() {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function(match, number) {
            return typeof args[number] != 'undefined' ? args[number] : match;
        });
    };
}

$(document).ready(function() {
    $('#donoVideo').on('ended', function() {
        NextDonation();
    });
    connect_to_ws();
});

let donoQueue = [];
let highlightQueue = [];
let fadeOutTimer = null;
let notificationMessage = null;
let playAudio = new Audio();
playAudio.volume = 0.3; // Object initialiser?

playAudio.addEventListener('canplaythrough', function() {
    setTimeout(function() {
        playAudio.play();
    }, 1000);
});

playAudio.addEventListener('ended', function() {
    var currentNotif = notificationMessage;
    setTimeout(function() {
        currentNotif.textillate('out');
        currentNotif.animate(
            {
                height: 0,
                opacity: 0,
            },
            1000
        );

        if (highlightQueue.length > 0) {
            PlayHighlights();
        }
    }, 2000);
});

function add_random_box({ color }) {
    var divsize = 50;
    var posx = (Math.random() * ($(document).width() - divsize)).toFixed();
    var posy = (Math.random() * ($(document).height() - divsize)).toFixed();
    var $newdiv = $("<div class='exploding'></div>").css({
        left: posx + 'px',
        top: posy + 'px',
        'background-color': color,
        opacity: 0,
    });
    $newdiv.appendTo('body');
    $newdiv.animate(
        {
            opacity: 1,
        },
        500
    );
    setTimeout(function() {
        $newdiv.animate(
            {
                opacity: 0,
            },
            1000
        );
        setTimeout(function() {
            $newdiv.remove();
        }, 1000);
    }, 5000);
}

function getEmoteURL({ urls }) {
    let sortedSizes = Object.keys(urls)
        .map(size => parseInt(size, 10))
        .sort();
    let largestSize = sortedSizes[sortedSizes.length - 1];
    return {
        url: urls[String(largestSize)],
        needsScale: 4 / largestSize,
    };
}

// opacity = number between 0 and 100
function add_emotes({
    emotes,
    opacity,
    persistence_time: persistenceTime,
    scale: emoteScale,
}) {
    for (let emote of emotes) {
        // largest URL available
        let { url, needsScale } = getEmoteURL(emote);

        let divsize = 250;
        let posx = (Math.random() * ($(window).width() - divsize)).toFixed();
        let posy = (Math.random() * ($(window).height() - divsize)).toFixed();
        let newdiv = $('<img class="absemote">').css({
            left: posx + 'px',
            top: posy + 'px',
            opacity: 0,
            transform: `scale(${(emoteScale / 100) * needsScale})`,
        });
        newdiv.attr({ src: url });
        newdiv.appendTo('body');
        newdiv.animate(
            {
                opacity: opacity / 100,
            },
            500
        );
        setTimeout(() => {
            newdiv.animate(
                {
                    opacity: 0,
                },
                1000
            );
            setTimeout(() => {
                newdiv.remove();
            }, 1000);
        }, persistenceTime);
    }
}

function show_custom_image(data) {
    var url = data.url;
    var divsize = 120;
    var posx = (Math.random() * ($(document).width() - divsize)).toFixed();
    var posy = (Math.random() * ($(document).height() - divsize)).toFixed();
    var css_data = {
        left: posx + 'px',
        top: posy + 'px',
        opacity: 0,
    };
    if (data.width !== undefined) {
        css_data.width = data.width;
    }
    if (data.height !== undefined) {
        css_data.height = data.height;
    }
    if (data.x !== undefined) {
        css_data.left = data.x + 'px';
    }
    if (data.y !== undefined) {
        css_data.top = data.y + 'px';
    }
    var $newdiv = $('<img class="absemote" src="' + url + '">').css(css_data);
    $newdiv.appendTo('body');
    $newdiv.animate(
        {
            opacity: 1,
        },
        500
    );
    setTimeout(function() {
        $newdiv.animate(
            {
                opacity: 0,
            },
            1000
        );
        setTimeout(function() {
            $newdiv.remove();
        }, 1000);
    }, 5000);
}

var message_id = 0;

function add_notification({ message, length, extra_classes }) {
    var new_notification = $(
        `<div class="${extra_classes}">${message}</div>`
    ).prependTo('div.notifications');
    new_notification.textillate({
        autostart: false,
        in: {
            effect: 'bounceInLeft',
            delay: 5,
            delayScale: 1.5,
            sync: false,
            shuffle: false,
            reverse: false,
        },
        out: {
            effect: 'bounceOutLeft',
            sync: true,
            shuffle: false,
            reverse: false,
        },
        type: 'word',
    });
    new_notification.on('inAnimationEnd.tlt', function() {
        setTimeout(function() {
            new_notification.textillate('out');
            new_notification.animate(
                {
                    height: 0,
                    opacity: 0,
                },
                1000
            );
        }, length * 1000);
    });
    new_notification.on('outAnimationEnd.tlt', function() {
        setTimeout(function() {
            new_notification.remove();
        }, 250);
    });

    return new_notification;
}

function refresh_combo_count(count) {
    $('#emote_combo span.count').html(count);
    $('#emote_combo span.count').addClass('animated pulsebig');
    $('#emote_combo span.count').on(
        'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
        function() {
            $(this).removeClass('animated pulsebig');
        }
    );
    $('#emote_combo img').addClass('animated pulsebig');
    $('#emote_combo img').on(
        'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
        function() {
            $(this).removeClass('animated pulsebig');
        }
    );
}

// https://gist.github.com/mkornblum/1384495
// slightly altered
$.fn.detachThenReattach = function(fn) {
    return this.each(function() {
        let $this = $(this);
        let tmpElement = $('<div style="display: none"/>');
        $this.after(tmpElement);
        $this.detach();
        fn.call($this);
        tmpElement.replaceWith($this);
    });
};

function refresh_combo_emote(emote) {
    let { url, needsScale } = getEmoteURL(emote);
    let $emoteCombo = $('#emote_combo img');

    // Fix for issue #378
    // we detach the <img> element from the DOM, then edit src and zoom,
    // then it is reattached where it used to be. This prevents the GIF animation
    // from resetting on all other emotes with the same URL on the screen
    $emoteCombo.detachThenReattach(function() {
        this.attr('src', url);
        this.css('zoom', String(needsScale));
    });
}

function debug_text(text) {
    //add_notification(text);
}

let current_emote_code = null;
let close_down_combo = null;

function refresh_emote_combo({ emote, count }) {
    let emote_combo = $('#emote_combo');
    if (emote_combo.length === 0) {
        current_emote_code = emote.code;
        let message = `x<span class="count">${count}</span> <img class="comboemote" /> combo!`;
        let new_notification = $(
            `<div id="emote_combo">${message}</div>`
        ).prependTo('div.notifications');
        new_notification.addClass('animated bounceInLeft');

        new_notification.on(
            'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
            function() {
                if (new_notification.hasClass('ended')) {
                    new_notification.animate(
                        {
                            height: 0,
                            opacity: 0,
                        },
                        500
                    );
                    setTimeout(function() {
                        new_notification.remove();
                    }, 500);
                }
            }
        );

        clearTimeout(close_down_combo);
        close_down_combo = setTimeout(function() {
            new_notification.addClass('animated bounceOutLeft ended');
        }, 4000);
    } else {
        clearTimeout(close_down_combo);
        close_down_combo = setTimeout(function() {
            emote_combo.addClass('animated bounceOutLeft ended');
        }, 3000);
    }

    refresh_combo_emote(emote);
    refresh_combo_count(count);
}

function create_object_for_win(points) {
    return {
        value: points,
        color: '#64DD17',
    };
}

function create_object_for_loss(points) {
    return {
        value: points,
        color: '#D50000',
    };
}

var hsbet_chart = false;

function hsbet_set_data(win_points, loss_points) {
    if (hsbet_chart !== false) {
        hsbet_chart.segments[0].value = win_points;
        hsbet_chart.segments[1].value = loss_points;
        hsbet_chart.update();
    }
}

function create_graph(win, loss) {
    var ctx = $('#hsbet .chart')
        .get(0)
        .getContext('2d');
    if (win == 0) {
        win = 1;
    }
    if (loss == 0) {
        loss = 1;
    }
    var data = [create_object_for_win(win), create_object_for_loss(loss)];
    var options = {
        animationSteps: 100,
        animationEasing: 'easeInOutQuart',
        segmentShowStroke: false,
    };
    if (hsbet_chart === false || true) {
        hsbet_chart = new Chart(ctx).Pie(data, options);
    } else {
        hsbet_set_data(win, loss);
    }
}

function NextDonation() {
    setTimeout(function() {
        if (donoQueue.length == 0) {
            fadeOutTimer = $('#donations').fadeOut(1000);
            return;
        }

        var currentDono = donoQueue.shift();

        $('#donoVideo').attr('src', currentDono.media);
        $('#donoVideo')[0].load();
        $('#donoHeader').html(
            `<span class="green">${currentDono.author}</span> just donated <span class="green">${currentDono.amount}</span>`
        );
        $('#donoText').text(currentDono.text);

        $('#donoVideo').on('loadeddata', function() {
            clearTimeout(fadeOutTimer);
            $('#donations')
                .stop()
                .fadeIn();

            $('#donations').fadeIn('slow', function() {
                $('#donoVideo')[0].play();
            });
        });
    }, 5000);
}

function ProcessDonations() {
    if ($('#donoVideo')[0].ended || Number.isNaN($('#donoVideo')[0].duration)) {
        NextDonation();
    }
}

function receive_donation(data) {
    donoQueue.push(data);
    ProcessDonations();
}

function PlayHighlights() {
    if (!playAudio.ended && playAudio.src != '') {
        return;
    }

    var currentHighlight = highlightQueue.shift();
    playAudio.src = 'data:audio/mp3;base64,' + currentHighlight.speech;
    playAudio.load();

    // playAudio.duration is sometimes infinite for some reason
    notificationMessage = add_notification({
        message: `<span class="user">${currentHighlight.user}</span> <span style="color: orange;">(${currentHighlight.voice})</span>: ${currentHighlight.message}`,
        length: 500,
        extra_classes: 'tts',
    });
}

function receive_highlight(data) {
    highlightQueue.push(data);
    if (highlightQueue.length == 1) {
        PlayHighlights();
    }
}

function skip_highlight() {
    playAudio.pause();
    playAudio.removeAttribute('src');
    notificationMessage.textillate('out');
    notificationMessage.animate(
        {
            height: 0,
            opacity: 0,
        },
        1000
    );

    if (highlightQueue.length > 0) {
        PlayHighlights();
    }
}

function start_emote_counter({ emote1, emote2 }) {
    var { url, needsScale } = getEmoteURL(emote1);
    $('#e1Img').attr('src', url);
    $('#e2Img').css('zoom', String(needsScale));

    var { url, needsScale } = getEmoteURL(emote2);
    $('#e2Img').attr('src', url);
    $('#e2Img').css('zoom', String(needsScale));

    $('#e1Text').text('0');
    $('#e2Text').text('0');

    $('#emotecounter').fadeIn(1000);
}

function update_emote_counter({ value1, value2 }) {
    $('#e1Text').text(value1);
    $('#e2Text').text(value2);
}

function close_emote_counter() {
    $('#emotecounter').fadeOut(6000, function() {
        $('#e1Text').text('');
        $('#e2Text').text('');

        $('#e1Img').removeAttr('src');
        $('#e1Img').removeAttr('style');
        $('#e2Img').removeAttr('src');
        $('#e2Img').removeAttr('style');
    });
}

function win_percent_change({ isRadiant, isDraw, winPct }) {
    if (Math.floor(Math.random() * 20) == 1) {
        $('#radiantImg').css('display', 'inline-block');
        $('#direImg').css('display', 'inline-block');
        $('#winText').css('display', 'relative');
    }

    if (isRadiant) {
        $('#radiantImg').css({ opacity: 1, border: '3px solid cyan' });
        $('#direImg').css({ opacity: 0.5, border: '' });
    } else {
        $('#radiantImg').css({ opacity: 0.5, border: '' });
        $('#direImg').css({ opacity: 1, border: '3px solid darkred' });
    }

    if (isDraw) {
        $('#radiantImg').css({ opacity: 1, border: '3px solid cyan' });
        $('#direImg').css({ opacity: 1, border: '3px solid darkred' });
    }

    $('#winText').text(winPct);
}

function win_percent_open() {
    $('#radiantImg').fadeIn(800, function() {});
    $('#direImg').fadeIn(800, function() {});
    $('#winText').fadeIn(800, function() {});
}

function win_percent_close() {
    setTimeout(function() {
        $('#radiantImg').fadeOut(3000, function() {});
        $('#direImg').fadeOut(3000, function() {});
        $('#winText').fadeOut(3000, function() {});
    }, 4000);
}

function bet_new_game() {
    var bet_el = $('#bet');
    bet_el.find('.left').css({
        visibility: 'visible',
        opacity: 1,
    });

    bet_el.hide();

    $('#winbetters').text('0');
    $('#lossbetters').text('0');
    $('#winpoints').text('0');
    $('#losspoints').text('0');

    bet_el.find('.left').show();
    bet_el.fadeIn(1000, function() {
        console.log('Faded in');
    });
}

function bet_update_data({ win: win_points, loss: loss_points }) {
    if (win_points > 0) {
        $('#winbetters').text(parseInt($('#winbetters').text(), 10) + 1);
        $('#winpoints').text(parseInt($('#winpoints').text(), 10) + win_points);
    } else {
        $('#lossbetters').text(parseInt($('#lossbetters').text(), 10) + 1);
        $('#losspoints').text(
            parseInt($('#losspoints').text(), 10) + loss_points
        );
    }
}

function bet_close_bet() {
    var bet_el = $('#bet');
    bet_el.fadeOut(10000, function() {
        bet_el.find('.left').css('visibility', 'hidden');
    });
}

function play_sound({ link, volume, rate }) {
    let player = new Howl({
        src: [link],
        volume: volume * 0.01, // the given volume is between 0 and 100
        rate: rate,
        onend: () => console.log('Playsound audio finished playing'),
        onloaderror: e => console.warn('audio load error', e),
        onplayerror: e => console.warn('audio play error', e),
    });

    player.play();
}

function play_custom_sound(url) {
    var audio = new Audio(url);
    audio.volume = 0.28;
    audio.play();
}

function handleWebsocketData(json_data) {
    if (json_data['event'] === undefined) {
        return;
    }

    let data = json_data.data;
    switch (json_data['event']) {
        case 'new_box':
            add_random_box(data);
            break;
        case 'new_emotes':
            add_emotes(data);
            break;
        case 'notification':
            !('length' in data) && (data.length = 2);
            add_notification(data);
            break;
        case 'timeout':
            add_notification({
                message:
                    '<span class="user">' +
                    data.user +
                    '</span> timed out <span class="victim">' +
                    data.victim +
                    '</span> with !timeout EleGiggle',
                length: 8,
            });
            break;
        case 'play_sound':
            !('rate' in data) && (data.rate = 1.0);
            play_sound(data);
            break;
        case 'donation':
            receive_donation(data);
            break;
        case 'highlight':
            receive_highlight(data);
            break;
        case 'skip_highlight':
            skip_highlight();
            break;
        case 'emote_combo':
            refresh_emote_combo(data);
            break;
        case 'emotecounter_start':
            start_emote_counter(data);
            break;
        case 'emotecounter_update':
            update_emote_counter(data);
            break;
        case 'emotecounter_close':
            close_emote_counter();
            break;
        case 'win_percent_change':
            win_percent_change(data);
            break;
        case 'win_percent_open':
            win_percent_open();
            break;
        case 'win_percent_close':
            win_percent_close();
            break;
        case 'bet_new_game':
            bet_new_game();
            break;
        case 'bet_update_data':
            bet_update_data(data);
            break;
        case 'bet_close_game':
            bet_close_bet();
            break;
        case 'show_custom_image':
            show_custom_image(data);
            break;
        case 'refresh':
        case 'reload':
            location.reload(true);
            break;
    }
}

let socket = null;

function connect_to_ws() {
    if (socket != null) {
        return;
    }

    console.log('Connecting to websocket....');
    socket = new WebSocket(ws_host);
    socket.binaryType = 'arraybuffer';
    socket.onopen = function() {
        console.log('WebSocket Connected!');
    };
    socket.onerror = function(event) {
        console.error('WebSocket error observed:', event);
    };
    socket.onmessage = function(e) {
        if (typeof e.data != 'string') {
            return;
        }

        let json_data = JSON.parse(e.data);
        console.log('Received data:', json_data);
        handleWebsocketData(json_data);
    };
    socket.onclose = function(e) {
        console.log(
            `WebSocket closed ${e.wasClean ? '' : 'un'}cleanly with reason ${
                e.code
            }: ${e.reason}`
        );
        socket = null;
        setTimeout(connect_to_ws, 2500);
    };
}
