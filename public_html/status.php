<?php
define('PUBLIC_HTML', true);
header('Cache-control: no-cache');
header('Access-Control-Allow-Origin: *');
header('Content-type: text/plain');

ini_set('user_agent', '-');

function ping_server($server) {
        $url = 'https://tools.wmflabs.org/phetools/' . $server . '?cmd=ping';
	$response = file_get_contents($url);
	return json_decode($response, true);
}

$serverlist = array(
	//'dummy_robot.php',
	'ocr.php',
	'hocr_cgi.py',
	'modernization_cgi.py',
	'match_and_split.php',
	'extract_text_layer.php',
	'verify_match.php',
	'credits.py',
	'pdf_to_djvu_cgi.py',
	'pages_without_scan.py',
);

foreach ($serverlist as $servername) {
	$answer = ping_server($servername);
	printf("ping: %s, error: %d, %s: %s, %.0f ms\n",
	       $servername, $answer['error'], $answer['text'],
	       $answer['server'], $answer['ping'] * 1000);
}
