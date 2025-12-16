const BASE_URL = 'http://localhost:3002/api/v1'

// Forms para as três abas de classificação
const fragmentForm = document.getElementById('fragmentForm')
const fragmentResult = document.getElementById('fragmentResult')

const domainForm = document.getElementById('domainForm')
const domainResult = document.getElementById('domainResult')

const completeForm = document.getElementById('completeForm')
const completeResult = document.getElementById('completeResult')

// Forms utilitários
const mapForm = document.getElementById('mapForm')
const mapResult = document.getElementById('mapResult')

const evalForm = document.getElementById('evaluateForm')
const evalResult = document.getElementById('evalResult')

function show(obj, el){ el.textContent = JSON.stringify(obj, null, 2) }

async function postForm(path, formEl){
  const fd = new FormData(formEl)
  try{
    const res = await fetch(BASE_URL + path, { method:'POST', body: fd })
    const data = await res.json().catch(()=>null)
    if(!res.ok){
      return {ok:false, status:res.status, data }
    }
    return {ok:true, status:res.status, data}
  } catch(e){
    return {ok:false, status:'NETWORK', data: {error: String(e)}}
  }
}

// Handler genérico para classificação
function handleClassificationSubmit(formEl, resultEl) {
  return async (ev) => {
    ev.preventDefault()
    if (!formEl.checkValidity()) {
      formEl.reportValidity()
      return
    }
    resultEl.textContent = 'Sending...'
    const r = await postForm('/run', formEl)
    if(r.ok){
      const d = r.data || {}
      const jobId = d.jobId || d.jobid || d.job || null
      const outputDir = d.outputDir || d.output || d.output_dir || null
      const serverMessage = d.message || ''

      let html = `<div class="result-success"><strong>Job queued successfully.</strong></div>`
      if(jobId) html += `<div style="margin-top:6px">Job ID: <code>${jobId}</code></div>`
      if(outputDir) html += `<div style="margin-top:6px">Output directory: <code>${outputDir}</code></div>`
      if(serverMessage) html += `<div class="muted" style="margin-top:6px">${serverMessage}</div>`
      html += `<div style="margin-top:8px">Result files and reports will be emailed to the address you provided once processing completes.</div>`

      resultEl.innerHTML = html
    } else {
      const errMsg = (r.data && (r.data.error || r.data.message)) ? (r.data.error || r.data.message) : JSON.stringify(r.data || {})
      resultEl.textContent = `Error (${r.status})\n${errMsg}`
    }
  }
}

// Attach handlers para os três forms de classificação
if (fragmentForm) fragmentForm.addEventListener('submit', handleClassificationSubmit(fragmentForm, fragmentResult))
if (domainForm) domainForm.addEventListener('submit', handleClassificationSubmit(domainForm, domainResult))
if (completeForm) completeForm.addEventListener('submit', handleClassificationSubmit(completeForm, completeResult))

mapForm.addEventListener('submit', async (ev)=>{
  ev.preventDefault()
  if (!mapForm.checkValidity()) {
    mapForm.reportValidity()
    return
  }
  mapResult.textContent = 'Sending...'
  const r = await postForm('/map-labels', mapForm)
  if(r.ok){
    show(r.data, mapResult)
  } else {
    mapResult.textContent = `Error (${r.status})\n` + JSON.stringify(r.data || {}, null, 2)
  }
})

evalForm.addEventListener('submit', async (ev)=>{
  ev.preventDefault()
  if (!evalForm.checkValidity()) {
    evalForm.reportValidity()
    return
  }
  evalResult.textContent = 'Sending...'
  const r = await postForm('/evaluate', evalForm)
  if(r.ok){
    show(r.data, evalResult)
  } else {
    evalResult.textContent = `Error (${r.status})\n` + JSON.stringify(r.data || {}, null, 2)
  }
})

// small helper: show when network available
window.addEventListener('load', ()=>{
  setupTabs()
  wireFragmentModelOptions()
})

function setupTabs(){
  const tabs = document.querySelectorAll('.tab')
  const contents = document.querySelectorAll('.tabContent')
  function activate(tabEl){
    tabs.forEach(t=> t.classList.remove('active'))
    contents.forEach(c=> c.classList.remove('active'))
    tabEl.classList.add('active')
    const id = tabEl.getAttribute('data-tab')
    const target = document.getElementById(id)
    if(target) target.classList.add('active')
  }
  tabs.forEach(t=> t.addEventListener('click', (e)=> { activate(e.currentTarget) }))
}

// ----- MODEL LISTS (populated from repo snapshot, kept in frontend only) -----
const CLASSIFYTE_MODELS = [
  'ClassifyTE_combined',
  'ClassifyTE_pgsb',
  'ClassifyTE_repbase'
]

const TERL_MODELS = [
  'DS1',
  'DS3'
]

<<<<<<< Updated upstream
const YORO_MODELS = [
  'AAqqYOLOqqdomainqqV21',
  'AAqqYOLOqqdomainqqV25'
]

const INPACTOR2_MODELS = [
  'Inpactor2'
]

=======
>>>>>>> Stashed changes
function showElement(id, show=true){
  const el = document.getElementById(id)
  if(!el) return
  if(show) el.classList.remove('hidden')
  else el.classList.add('hidden')
}

function setSelectOptions(selectEl, options){
  selectEl.innerHTML = ''
  options.forEach(opt => {
    const o = document.createElement('option')
    o.value = opt
    o.textContent = opt
    selectEl.appendChild(o)
  })
}

<<<<<<< Updated upstream
function wireRunModelOptions(){
  const modelSelect = document.querySelector('#runForm select[name="model"]')
  const modelFileSelect = document.getElementById('modelFileSelect')
  const terlModelList = document.getElementById('terlModelList')
  const classModelList = document.getElementById('classifyteModelList')
  const yoroModelList = document.getElementById('yoroModelList')
=======
function wireFragmentModelOptions(){
  const modelSelect = document.getElementById('fragmentModel')
  const modelFileSelect = document.getElementById('fragmentModelFileSelect')
  const modelFileLabel = document.getElementById('fragmentModelFileLabel')
>>>>>>> Stashed changes

  if(!modelSelect || !modelFileSelect) return

  // init lists with ClassifyTE as default
  setSelectOptions(modelFileSelect, CLASSIFYTE_MODELS)
<<<<<<< Updated upstream
  terlModelList.innerHTML = TERL_MODELS.map(m => `<li>${m}</li>`).join('\n')
  if(classModelList) classModelList.innerHTML = CLASSIFYTE_MODELS.map(m => `<li>${m}</li>`).join('\n')
  if(yoroModelList) yoroModelList.innerHTML = YORO_MODELS.map(m => `<li>${m}</li>`).join('\n')

  function updateForModel(){
    const model = modelSelect.value
    // hide all model-specific areas first
    document.querySelectorAll('.model-specific').forEach(el => el.classList.add('hidden'))
=======

  function updateForModel(){
    const model = modelSelect.value
    
    // hide all model-specific areas first
    showElement('fragmentClassifyteOpts', false)
    showElement('fragmentTerlOpts', false)
>>>>>>> Stashed changes

    if(model === 'classifyte'){
      setSelectOptions(modelFileSelect, CLASSIFYTE_MODELS)
      showElement('fragmentClassifyteOpts', true)
    } else if(model === 'terl'){
      // show a simple list and a model-file select tailored for TERL
      setSelectOptions(modelFileSelect, TERL_MODELS)
<<<<<<< Updated upstream
      showElement('terlOpts', true)
    } else if(model === 'yoro'){
      setSelectOptions(modelFileSelect, YORO_MODELS)
      showElement('yoroOptions', true)
    } else if(model === 'inpactor2'){
      setSelectOptions(modelFileSelect, INPACTOR2_MODELS)
      showElement('inpactor2Options', true)
    }
    // Enable inputs for visible model-specific section and disable inputs in hidden sections
    document.querySelectorAll('.model-specific').forEach(section => {
      const isHidden = section.classList.contains('hidden')
      section.querySelectorAll('input, select, textarea').forEach(control => {
        control.disabled = isHidden
      })
    })
=======
      showElement('fragmentTerlOpts', true)
    }
>>>>>>> Stashed changes
  }

  modelSelect.addEventListener('change', updateForModel)
  // call once to set correct initial state
  updateForModel()
}
