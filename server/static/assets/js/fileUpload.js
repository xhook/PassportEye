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



		// Custom XMLHttpRequest
		// xhr: function() {
		// 	var myXhr = $.ajaxSettings.xhr();
		// 	if (myXhr.upload) {
		// 		For handling the progress of the upload
				// myXhr.upload.addEventListener('progress', function(e) {
				// 	if (e.lengthComputable) {
				// 		$('progress').attr({
				// 			value: e.loaded,
				// 			max: e.total
				// 		});
				// 	}
				// } , false);
			// }
			// return myXhr;
		// }
	});

	fetch("http://0.0.0.0:5001/upload_file",
	{
	    method: "POST",
	    body: new FormData($('form')[0])
	})
	.then(response => {
	  response.blob().then(blobResponse => {
	    data = blobResponse;
	    const urlCreator = window.URL || window.webkitURL;
	    $('#blah').attr('src', urlCreator.createObjectURL(data));

	    // Now get confidence score if needed
	   	$.ajax({
			url: 'http://0.0.0.0:5001/is_human',
			type: 'GET',
			success: function(response) {
				// response is the confidence score
				console.log(response)
			}
		})
	  })
	})
});

})(jQuery, window.Dropzone);
