'use client'

import React, { Fragment } from 'react'
import { Menu, Transition } from '@headlessui/react'
import { EllipsisVerticalIcon, PencilIcon, TrashIcon } from '@heroicons/react/20/solid' // 需要安装 @heroicons/react

interface ConversationActionsProps {
    conversationId: string;
    onRename: (id: string) => void; // 假设有重命名功能
    onDelete: (id: string, e: React.MouseEvent) => void;
}

const ConversationActions: React.FC<ConversationActionsProps> = ({ conversationId, onRename, onDelete }) => {
    return (
        <Menu as="div" className="relative inline-block text-left shrink-0"> {/* shrink-0 防止被压缩 */}
            <div>
                <Menu.Button className="inline-flex justify-center rounded-md px-1 py-1 text-sm font-medium text-gray-500 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75">
                    <EllipsisVerticalIcon className="h-5 w-5" aria-hidden="true" />
                </Menu.Button>
            </div>
            <Transition
                as={Fragment}
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95"
            >
                <Menu.Items className="absolute right-0 z-10 mt-2 w-32 origin-top-right divide-y divide-gray-100 rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                    <div className="px-1 py-1 ">
                        {/* <Menu.Item>
              {({ active }) => (
                <button
                  onClick={() => onRename(conversationId)}
                  className={`${active ? 'bg-blue-500 text-white' : 'text-gray-900'
                    } group flex w-full items-center rounded-md px-2 py-2 text-sm`}
                >
                  <PencilIcon className="mr-2 h-4 w-4" aria-hidden="true" />
                  重命名
                </button>
              )}
            </Menu.Item> */} // 暂时注释掉重命名
                        <Menu.Item>
                            {({ active }) => (
                                <button
                                    onClick={(e) => onDelete(conversationId, e)} // 传递事件对象
                                    className={`${active ? 'bg-red-500 text-white' : 'text-gray-900'
                                        } group flex w-full items-center rounded-md px-2 py-2 text-sm`}
                                >
                                    <TrashIcon className="mr-2 h-4 w-4" aria-hidden="true" />
                                    删除
                                </button>
                            )}
                        </Menu.Item>
                    </div>
                </Menu.Items>
            </Transition>
        </Menu>
    )
}

export default ConversationActions 