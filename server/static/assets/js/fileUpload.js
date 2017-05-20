(function($, Dropzone){

console.log("INVOKED fileUpload.js");
console.log(Dropzone);
// "myAwesomeDropzone" is the camelized version of the HTML element's ID
// The recommended way from within the init configuration:
Dropzone.options.myAwesomeDropzone = {
    init: function() {
        this.on("success", function(file, response) {
            $("#json-output").html(JSON.stringify(response, null, 2));
       });
    }
};
Dropzone.options.thumbnailHeight = 240;
Dropzone.options.thumbnailWidth = 240;
})(jQuery, window.Dropzone);

function readURL(input) {

	if (input.files && input.files[0]) {
		var reader = new FileReader();

		reader.onload = function (e) {
			$('#blah').attr('src', e.target.result);
		};

		reader.readAsDataURL(input.files[0]);
	}
}

$(':file').on('change', function() {
	var file = this.files[0];
	if (file.size > 1024*1024*10) {
		alert('max upload size is 1k')
	}

	readURL(this);
	// Also see .name, .type
});


$(':button').on('click', function() {
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
			$('#json-output').html(JSON.stringify(response, null, 2));
		}

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
});

$('#upload_button').click()