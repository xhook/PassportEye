(function ($) {

	var imageWithBBUrl = null;
	var confidenceScore = null;

	function readURL(input) {
		imageWithBBUrl = null;
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
		fetch("http://178.62.204.148:5001/upload_file", {
			method: "POST",
			body: new FormData($('form')[0])
		})
		.then(function(response) {
			response.blob().then(function(blobResponse) {
				data = blobResponse;
				const urlCreator = window.URL || window.webkitURL;
				imageWithBBUrl = urlCreator.createObjectURL(data);

				// Now get confidence score if needed
				$.ajax({
					url: 'http://178.62.204.148:5001/is_human',
					type: 'GET',
					success: function(response) {
						confidenceScore = response;
						// response is the confidence score
						console.log(response)
					}
				});
			});
		});

	});

	$('#human_readable_box_no_result').show();
	$('#human_readable_box_failure').hide();
	$('#human_readable_box_success').hide();

	var successCb = function (response) {
		$('.loader').hide();
		$('#json-output').text(JSON.stringify(response, null, 4));
		if (response['valid']) {
			if (imageWithBBUrl !== null) {
				$('#blah').attr('src', imageWithBBUrl);
			}
			$('#human_readable_box_no_result').hide();
			$('#human_readable_box_failure').hide();
			$('#human_readable_box_success').show();

		} else {
			$('#human_readable_box_no_result').hide();
			$('#human_readable_box_failure').show();
			$('#human_readable_box_success').hide();
		}
	};

	$('.loader').hide();

	$(':button').on('click', function () {
		// successCb({
		// 	'score': 0.99,
		// 	'valid': false,
		// 	'metadata': {
		// 		'first_name': 'Foo',
		// 		'last_name': 'Bar'
		// 	}
		// });
		// return;
		$('.loader').show();

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
			success: successCb,
			failure: function () {
				$('.loader').hide();
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
	});


})(jQuery);
