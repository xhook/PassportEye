(function ($) {

	function readURL(input) {
		if (input.files && input.files[0]) {
			var reader = new FileReader();
			reader.onload = function (e) {
				$('#blah').attr('src', e.target.result);
			};
			reader.readAsDataURL(input.files[0]);
		}
	}

	$(':file').on('change', function () {
		var file = this.files[0];
		if (file.size > 1024 * 1024 * 10) {
			alert('max upload size is 1k')
		}

		readURL(this);
	});


	$(':button').on('click', function () {
		$.ajax({
			// Your server script to process the upload
			url: 'verify',
			type: 'POST',

			// Form data
			data: new FormData($('form')[0]),

			// Tell jQuery not to process data or worry about content-type
			// You *must* include these options!
			cache: false,
			contentType: false,
			processData: false,
			success: function (response) {
				$('#json-output').text(JSON.stringify(response, null, 4));
				if (response['valid']) {
					$('#human_readable_box').html('<img src="/static/images/checkmark-xxl.png" />')
				} else {
					$('#human_readable_box').html('Go away')
				}
			}
		});
	});

	var show = 'human_readable_box';
	$('#code_box').hide();

	$('#switcher').on('click', function () {
		$('#code_box').hide();
		$('#human_readable_box').hide();
		if (show == 'human_readable_box') {
			show = 'code_box';
			$('#code_box').show();
			$('#switcher').text('Show result')
		} else {
			show = 'human_readable_box';
			$('#human_readable_box').show();
			$('#switcher').text('Show response')
		}
	})

})(jQuery, window.Dropzone);

