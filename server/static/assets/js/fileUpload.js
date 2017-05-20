(function($, Dropzone){

console.log("INVOKED fileUpload.js");
console.log(Dropzone);
// "myAwesomeDropzone" is the camelized version of the HTML element's ID
// The recommended way from within the init configuration:
Dropzone.options.myAwesomeDropzone = {
    init: function() {
        this.on("success", function(file, response) {
            console.log(response);
        });
    }
};
})(jQuery, window.Dropzone);