import { useEffect, useRef, useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import { Node, mergeAttributes } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { TextStyle } from '@tiptap/extension-text-style'
import Color from '@tiptap/extension-color'
import api from '../../api'

// 轻量图片节点：复用 @tiptap/core 的 Node，不引入额外扩展包，规避 peer 版本冲突。
const ImageNode = Node.create({
  name: 'image',
  group: 'block',
  inline: false,
  draggable: true,
  addAttributes() {
    return {
      src: {},
      alt: { default: null },
      title: { default: null },
    }
  },
  parseHTML() {
    return [{ tag: 'img[src]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['img', mergeAttributes(HTMLAttributes)]
  },
})

const COLORS = ['#0f172a', '#2563eb', '#06b6d4', '#dc2626', '#059669', '#d97706', '#db2777']

const tb =
  'min-w-8 h-8 px-2 rounded-lg border border-white/75 text-[#475569] hover:bg-white/60 transition text-sm flex items-center justify-center'

export default function RichTextEditor({ value, onChange, placeholder }) {
  const editor = useEditor({
    extensions: [StarterKit, TextStyle, Color, ImageNode],
    content: value || '',
    editorProps: {
      attributes: {
        class:
          'rich-editor min-h-[60vh] max-h-[70vh] overflow-y-auto w-full px-4 py-3 text-sm leading-relaxed text-[#0f172a] focus:outline-none',
      },
    },
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
  })

  const fileRef = useRef(null)
  const [uploading, setUploading] = useState(false)

  // 外部 value 变化（切换记录等）时同步到编辑器，避免光标回环
  useEffect(() => {
    if (!editor) return
    const current = editor.getHTML()
    if (value !== current) {
      editor.commands.setContent(value || '', { emitUpdate: false })
    }
  }, [value, editor])

  if (!editor) return null

  const onPickImage = () => fileRef.current?.click()
  const onFile = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = '' // 允许重复选同一文件
    if (!file) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const { data } = await api.post('/upload/image', fd)
      editor.chain().focus().insertContent(`<img src="${data.url}">`).run()
    } catch {
      alert('图片上传失败')
    } finally {
      setUploading(false)
    }
  }

  const btn = (active, onClick, children) => (
    <button
      type="button"
      onClick={onClick}
      className={`${tb} ${active ? 'bg-[#06b6d4]/15 border-[#06b6d4] text-[#0891b2]' : ''}`}
    >
      {children}
    </button>
  )

  return (
    <div className="relative">
      <div className="flex flex-wrap items-center gap-1.5 mb-2">
        {btn(editor.isActive('bold'), () => editor.chain().focus().toggleBold().run(), <b>B</b>)}
        {btn(editor.isActive('italic'), () => editor.chain().focus().toggleItalic().run(), <i>I</i>)}
        {btn(editor.isActive('underline'), () => editor.chain().focus().toggleUnderline().run(), <u>U</u>)}
        {btn(editor.isActive('strike'), () => editor.chain().focus().toggleStrike().run(), <s>S</s>)}
        <span className="w-px h-5 bg-white/75 mx-0.5" />
        {btn(
          editor.isActive('heading', { level: 1 }),
          () => editor.chain().focus().toggleHeading({ level: 1 }).run(),
          'H1',
        )}
        {btn(
          editor.isActive('heading', { level: 2 }),
          () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
          'H2',
        )}
        <span className="w-px h-5 bg-white/75 mx-0.5" />
        {btn(editor.isActive('bulletList'), () => editor.chain().focus().toggleBulletList().run(), '• 列表')}
        {btn(editor.isActive('orderedList'), () => editor.chain().focus().toggleOrderedList().run(), '1. 列表')}
        {btn(editor.isActive('blockquote'), () => editor.chain().focus().toggleBlockquote().run(), '❝')}
        <span className="w-px h-5 bg-white/75 mx-0.5" />
        {btn(false, onPickImage, uploading ? '…' : '🖼')}
        {COLORS.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => editor.chain().focus().setColor(c).run()}
            className={`w-6 h-6 rounded-lg border border-white/75 shadow-sm ${
              editor.isActive('textStyle', { color: c }) ? 'ring-2 ring-[#06b6d4]' : ''
            }`}
            style={{ backgroundColor: c }}
            title={c}
          />
        ))}
        <button
          type="button"
          onClick={() => editor.chain().focus().unsetColor().run()}
          className={tb}
          title="清除颜色"
        >
          ⌀
        </button>
      </div>

      {editor.isEmpty && placeholder && (
        <div className="absolute left-4 top-[44px] text-sm text-[#94a3b8] pointer-events-none">
          {placeholder}
        </div>
      )}

      <div className="border border-white/75 rounded-xl bg-white/70 focus-within:border-[#06b6d4] focus-within:ring-2 focus-within:ring-[#06b6d4]/20 transition">
        <EditorContent editor={editor} />
      </div>
      <input ref={fileRef} type="file" accept="image/*" hidden onChange={onFile} />
    </div>
  )
}
