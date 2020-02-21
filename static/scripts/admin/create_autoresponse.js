$(document).ready(function() {
    $('form').form({
        fields: {
            name: {
                identifier: 'name',
                rules: [
                    {
                        type: 'empty',
                        prompt: 'You must enter a name for your autoresponse',
                    },
                ],
            },
            trigger: {
                identifier: 'trigger',
                rules: [
                    {
                        type: 'empty',
                        prompt: 'The trigger cannot be empty',
                    },
                ],
            },
            response: {
                identifier: 'response',
                rules: [
                    {
                        type: 'empty',
                        prompt: 'The response cannot be empty',
                    },
                ],
            },
        },
        keyboardShortcuts: false,
        onSuccess: function(event, fields) {
            console.log(fields);
        },
    });
});
