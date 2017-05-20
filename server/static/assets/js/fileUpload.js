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
		$.ajax({
			// Your server script to process the upload
			url: 'upload_file',
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
			}
		});
	});


	$(':button').on('click', function () {
	});

})(jQuery, window.Dropzone);

