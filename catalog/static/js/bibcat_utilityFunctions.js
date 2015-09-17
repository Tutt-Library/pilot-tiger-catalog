function isNotNull (variable) {
	var result = true;
	if(variable === null && typeof variable === "object"){var result = false}; //Null Test
	if(variable === "" && typeof variable === "string"){var result = false}; //Empty String Test
	if(variable === undefined && typeof variable === "undefined"){var result = false}; //Undefined Test
	if(variable === "undefined"){var result = false}; //Undefined Test 2
	if(variable === false && typeof variable === "boolean"){var result = false}; //False Test
	if(variable === 0 && typeof variable === "number"){var result = false}; //Zero Test
	if(!parseFloat(variable) && variable != 0 && typeof variable === "number") {var result = false}; //NaN Test
	return result;
};

function readObj (obj, objNameArray) {
	var testObj = obj;
	for(var i=0;i<objNameArray.length;i++) {
		testObj = testObj[objNameArray[i]];
		if (!(isNotNull(testObj))) {
		 return false;
		}
	}
	return testObj;
};



